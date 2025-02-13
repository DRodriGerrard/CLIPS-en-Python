import xml.etree.ElementTree as ET
import os
import subprocess

def run_clips_and_get_java(clips_file):
    try:
        clips_path = r"C:\Program Files\SSS\CLIPS 6.4.2\CLIPSDOS.exe"
        absolute_clips_file = os.path.abspath(clips_file).replace("\\", "/")

        process = subprocess.Popen(
            clips_path, 
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        commands = f'(batch "{absolute_clips_file}")\n(reset)\n(run)\n(exit)\n'
        output, error = process.communicate(commands, timeout=10)

        if error:
            return f"Error ejecutando CLIPS:\n{error}"

        # 🔹 Guardar salida completa para depuración
        output_file_path = os.path.join(os.getcwd(), "output_java.txt")
        with open(output_file_path, "w", encoding="utf-8") as file:
            file.write(output)

        print(f"📂 Se guardó la salida en: {output_file_path}")

        # 🔹 Devolver la salida completa sin filtrar
        return output  

    except subprocess.TimeoutExpired:
        return "Error: CLIPS tardó demasiado en responder."
    except Exception as e:
        return f"Error ejecutando CLIPS: {e}"
    

def parse_xmi(file_path):
    tree = ET.parse(file_path)
    root = tree.getroot()
    print(f"Root element: {root.tag}")
    return root

def extract_classes(root):
    classes = []
    relationships = []

    print("🔎 Iniciando extracción de clases y relaciones desde XMI...")

    # Espacios de nombres
    ns = {
        'xmi': "http://schema.omg.org/spec/XMI/2.1",
        'uml': "http://www.omg.org/spec/UML/20090901"
    }

    # 🔍 Buscar clases dentro de `packagedElement` con `xmi:type="uml:Class"`
    for elem in root.findall('.//packagedElement'):
        if elem.get('{http://schema.omg.org/spec/XMI/2.1}type') == 'uml:Class':
            class_name = elem.get('name')
            if class_name:
                print(f"✔ Clase detectada: {class_name}")
                class_info = {
                    'name': class_name,
                    'attributes': [],
                    'operations': []
                }

                # Buscar atributos dentro de la clase
                for attr in elem.findall('ownedAttribute'):
                    attr_name = attr.get('name')
                    attr_visibility = attr.get('visibility', 'public')
                    attr_type = attr.get('type', 'None')

                    class_info['attributes'].append({
                        'name': attr_name,
                        'visibility': attr_visibility,
                        'type': attr_type
                    })
                    print(f"  ➜ Atributo encontrado: {attr_name} ({attr_type})")

                # Buscar operaciones dentro de la clase
                for op in elem.findall('ownedOperation'):
                    op_name = op.get('name')
                    op_visibility = op.get('visibility', 'public')
                    op_type = "void"

                    type_elem = op.find('type')
                    if type_elem is not None and 'name' in type_elem.attrib:
                        op_type = type_elem.attrib['name']

                    class_info['operations'].append({
                        'name': op_name,
                        'visibility': op_visibility,
                        'type': op_type
                    })
                    print(f"  ➜ Operación encontrada: {op_name}, Tipo: {op_type}")

                classes.append(class_info)
            else:
                print("⚠ Se encontró un `uml:Class` sin nombre.")

    print(f"📌 Clases detectadas en `extract_classes()`: {classes}")
    print("🔎 Extracción de clases y relaciones finalizada.")
    return classes, relationships

def extract_directed_associations(root, class_dict):
    obj_id=1
    directed_associations = []
    for elem in root.findall('.//packagedElement'):
        type_attr = elem.get('{http://schema.omg.org/spec/XMI/2.1}type')
        if type_attr == 'uml:DirectedAssociation':
            member_end = elem.get('memberEnd')
            if member_end:
                source, target = member_end.split()
                owned_ends = elem.findall('ownedEnd')
                multiplicity_source = None
                multiplicity_target = None
                for owned_end in owned_ends:
                    end_type = owned_end.get('type')
                    if end_type == source and  multiplicity_source == None:
                        multiplicity_source = owned_end.get('multiplicity1')
        
                    if end_type == target and multiplicity_target == None:
                        multiplicity_target = owned_end.get('multiplicity2')
                       
                #print(multiplicity_source)
                #print(multiplicity_target)    
                if source and target:
                    directed_associations.append({
                        'type': 'directedAssociation',
                        'source': source,
                        'target': target,
                        'multiplicity1': multiplicity_source,
                        'multiplicity2': multiplicity_target
                    })
                    # Añadir atributo en la clase source
                    class_name = source
                    if class_name in class_dict:
                        if multiplicity_target != "*":
                            class_dict[class_name]['attributes'].append({
                                'name': f'{target.lower()}List{obj_id}',
                                'visibility': 'private',
                                'type': f'{target}[]'
                            })
                            obj_id+=1
                        else:
                            class_dict[class_name]['attributes'].append({
                                'name': f'{target.lower()}List{obj_id}',
                                'visibility': 'private',
                                'type': f'HashSet<{target}>'
                            })
                            obj_id+=1
    return directed_associations

def extract_generalizations(root):
    generalizations = []
    for elem in root.findall('.//packagedElement'):
        type_attr = elem.get('{http://schema.omg.org/spec/XMI/2.1}type')
        if type_attr == 'uml:Generalization':
            memberEnd = elem.get('memberEnd')
            parent_name, child_name = memberEnd.split()
            if parent_name and child_name:
                generalizations.append({
                    'type': 'generalization',
                    'parent': parent_name,
                    'child': child_name
                })
    return generalizations

def extract_associations(root):
    associations = []
    for elem in root.findall('.//packagedElement'):
        type_attr = elem.get('{http://schema.omg.org/spec/XMI/2.1}type')
        if type_attr == 'uml:Association':
            member_end = elem.get('memberEnd')
            if member_end and len(member_end.split()) == 2:
                source, target = member_end.split()
                owned_ends = elem.findall('ownedEnd')
                multiplicity_source = "1..1"
                multiplicity_target = "1..1"

                for owned_end in owned_ends:
                    end_type = owned_end.get('type')
                    lower = owned_end.get('lowerValue', '1')  # Valor inferior de la multiplicidad
                    upper = owned_end.get('upperValue', '*')  # Valor superior de la multiplicidad

                    if end_type == source:
                        multiplicity_source = f"{lower}..{upper}"
                    elif end_type == target:
                        multiplicity_target = f"{lower}..{upper}"

                associations.append({
                    'type': 'association',
                    'source': source,
                    'target': target,
                    'multiplicity1': multiplicity_source,
                    'multiplicity2': multiplicity_target
                })
    return associations

def extract_dependencies(root):
    dependencies = []
    for elem in root.findall('.//packagedElement'):
        type_attr = elem.get('{http://schema.omg.org/spec/XMI/2.1}type')
        if type_attr == 'uml:Dependency':
            memberEnd = elem.get('memberEnd')
            if memberEnd:
                client, supplier = memberEnd.split()
                if client and supplier:
                    dependencies.append({
                        'type': 'dependency',
                        'client': client,
                        'supplier': supplier
                    })
    return dependencies

def extract_compositions(root):
    compositions = []
    for elem in root.findall('.//packagedElement'):
        type_attr = elem.get('{http://schema.omg.org/spec/XMI/2.1}type')
        if type_attr == 'uml:Composition':
            member_end = elem.get('memberEnd')
            if member_end:
                whole, part = member_end.split()
                owned_ends = elem.findall('ownedEnd')
                multiplicity_target = None
                for owned_end in owned_ends:
                    end_type = owned_end.get('type')
                    if end_type == part:
                        multiplicity_target = owned_end.get('multiplicity')
                if whole and part:
                    compositions.append({
                        'type': 'composition',
                        'whole': whole,
                        'part': part,
                        'multiplicity': multiplicity_target
                    })
    return compositions

def extract_aggregations(root):
    aggregations = []
    for elem in root.findall('.//packagedElement'):
        type_attr = elem.get('{http://schema.omg.org/spec/XMI/2.1}type')
        if type_attr == 'uml:Aggregation':
            member_end = elem.get('memberEnd')
            if member_end:
                whole, part = member_end.split()
                owned_ends = elem.findall('ownedEnd')
                multiplicity_target = None
                for owned_end in owned_ends:
                    end_type = owned_end.get('type')
                    if end_type == part:
                        multiplicity_target = owned_end.get('multiplicity')
                if whole and part:
                    aggregations.append({
                        'type': 'aggregation',
                        'whole': whole,
                        'part': part,
                        'multiplicity': multiplicity_target
                    })
    return aggregations

def generate_clips_facts(classes, relationships):
    clips_facts = []

    # **🔹 Definir correctamente los deftemplates**
    clips_facts.append('(deftemplate class (slot name) (multislot attributes) (multislot operations))')
    clips_facts.append('(deftemplate attribute (slot id) (slot class-name) (slot name) (slot visibility) (slot type))')
    clips_facts.append('(deftemplate operation (slot id) (slot class-name) (slot name) (slot visibility) (slot type))')
    clips_facts.append('(deftemplate dependency (slot client) (slot supplier))')
    clips_facts.append('(deftemplate generalization (slot parent) (slot child))')
    clips_facts.append('(deftemplate directedAssociation (slot source) (slot target) (slot multiplicity1) (slot multiplicity2))')
    clips_facts.append('(deftemplate association (slot source) (slot target) (slot multiplicity1) (slot multiplicity2))')
    clips_facts.append('(deftemplate composition (slot whole) (slot part) (slot multiplicity))')
    clips_facts.append('(deftemplate aggregation (slot whole) (slot part) (slot multiplicity))')

    clips_facts.append('(deffacts initial-facts')

    attribute_id = 1
    operation_id = 1

    for cls in classes:
        attributes = []
        operations = []

        for attr in cls['attributes']:
            attr_id = f'attr{attribute_id}'
            clips_facts.append(f'  (attribute (id "{attr_id}") (class-name "{cls["name"]}") (name "{attr["name"]}") (visibility "{attr["visibility"]}") (type "{attr["type"]}"))')
            attributes.append(f'"{attr_id}"')
            attribute_id += 1

        for op in cls['operations']:
            op_id = f'op{operation_id}'
            op_type = op.get("type", "void")

            # 🔎 Verificar que `op_type` tiene el valor correcto antes de escribir en CLP
            print(f"🚀 Verificando método antes de escribir en CLP: Clase={cls['name']}, Método={op['name']}, Tipo={op_type}")

            clips_facts.append(f'  (operation (id "{op_id}") (class-name "{cls["name"]}") '
                            f'(name "{op["name"]}") (visibility "{op["visibility"]}") (type "{op_type}"))')
            operations.append(f'"{op_id}"')
            operation_id += 1


        attributes_str = ' '.join(attributes) if attributes else 'nil'
        operations_str = ' '.join(operations) if operations else 'nil'
        print(f"✔ Agregando clase {cls['name']} con atributos {attributes_str} y operaciones {operations_str}")
        clips_facts.append(f'  (class (name "{cls["name"]}") (attributes {attributes_str}) (operations {operations_str}))')

    for rel in relationships:
        if rel['type'] == 'generalization':
            clips_facts.append(f'  (generalization (parent "{rel["parent"]}") (child "{rel["child"]}"))')
        elif rel['type'] == 'association':
            clips_facts.append(f'  (association (source "{rel["source"]}") (target "{rel["target"]}") (multiplicity1 "{rel["multiplicity1"]}") (multiplicity2 "{rel["multiplicity2"]}"))')

    clips_facts.append(')')  # Cierre de deffacts

    return clips_facts

def write_clips_file(clips_facts, file_path):
    try:
        print("📝 Contenido del archivo CLP antes de escribir:")
        for fact in clips_facts:
            print(fact)  # Muestra cada hecho en la consola

        with open(file_path, 'w') as file:
            for fact in clips_facts:
                file.write(f'{fact}\n')
            
            # Escribir reglas al final
            file.write('''
(defrule generate-java-code
   
   ?class <- (class (name ?class-name) (attributes $?attributes) (operations $?operations))
   (generalization (parent ?class-name) (child ?x))
   =>
   (printout t "// Java code for class " ?class-name crlf)
   (printout t "public class " ?class-name " extends " ?x " {" crlf)
   
   ;; Imprimir atributos
   (do-for-all-facts ((?attr attribute))
      (and
         (member$ (fact-slot-value ?attr id) $?attributes)
         (eq (fact-slot-value ?attr class-name) ?class-name))
      (bind ?visibility (fact-slot-value ?attr visibility))
      (bind ?type (fact-slot-value ?attr type))
      (bind ?name (fact-slot-value ?attr name))
      (printout t  "   " ?visibility " " ?type " " ?name ";" crlf))
   
   ;; Imprimir métodos
   (do-for-all-facts ((?op operation))
      (and
         (member$ (fact-slot-value ?op id) $?operations)
         (eq (fact-slot-value ?op class-name) ?class-name))
      (bind ?visibility (fact-slot-value ?op visibility))
      (bind ?type (fact-slot-value ?op type))
      (bind ?name (fact-slot-value ?op name))
      (printout t "   " ?visibility " " ?type " " ?name "()" " {" crlf
                "      // method body" crlf "   }" crlf))
   
   (printout t "}" crlf crlf)
)
                   
(defrule generate-java-code-no-inheritance
   ?class <- (class (name ?class-name) (attributes $?attributes) (operations $?operations))
   (not (generalization (parent ?class-name)))
    =>
   (printout t "// Java code for class " ?class-name crlf)
   (printout t "public class " ?class-name " {" crlf)
   
   ;; Imprimir atributos
   (do-for-all-facts ((?attr attribute))
      (and
         (member$ (fact-slot-value ?attr id) $?attributes)
         (eq (fact-slot-value ?attr class-name) ?class-name))
      (bind ?visibility (fact-slot-value ?attr visibility))
      (bind ?type (fact-slot-value ?attr type))
      (bind ?name (fact-slot-value ?attr name))
      (printout t  "   " ?visibility " " ?type " " ?name ";" crlf))
   
   ;; Imprimir métodos
   (do-for-all-facts ((?op operation))
      (and
         (member$ (fact-slot-value ?op id) $?operations)
         (eq (fact-slot-value ?op class-name) ?class-name))
      (bind ?visibility (fact-slot-value ?op visibility))
      (bind ?type (fact-slot-value ?op type))
      (bind ?name (fact-slot-value ?op name))
      (printout t "   " ?visibility " " ?type " " ?name "()" " {" crlf
                "      // method body" crlf "   }" crlf))
   
   (printout t "}" crlf crlf)
)
''')
        print(f"Archivo CLIPS guardado correctamente en {file_path}")

    except Exception as e:
        print(f"Error al escribir el archivo CLIPS: {str(e)}")

##############################################################################            

# Abre el archivo en modo lectura
xmi_file_path = 'generated/xmi/diagram.xmi'

if os.path.exists(xmi_file_path):
    with open(xmi_file_path, 'r') as archivo:
        xmi_data = archivo.read()
else:
    print(f"Error: No se encontró el archivo {xmi_file_path}")

# Archivo de salida CLIPS
clips_file = 'output.clp'

# try:
#     root = parse_xmi('example.xmi')
#     classes, class_dict = extract_classes(root)
#     generalizations = extract_generalizations(root)
#     directed_associations = extract_directed_associations(root, class_dict)
#     associations = extract_associations(root)
#     dependencies = extract_dependencies(root)
#     compositions = extract_compositions(root)
#     aggregations = extract_aggregations(root)
    
#     relationships = generalizations + directed_associations + associations + dependencies + compositions + aggregations
 
#     clips_facts = generate_clips_facts(classes, relationships)
#     write_clips_file(clips_facts, clips_file)
#     print("Archivo CLIPS generado correctamente.")
# except ET.ParseError as e:
#     print(f"Error al parsear el archivo XMI: {e}")
