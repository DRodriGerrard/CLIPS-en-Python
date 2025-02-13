import xml.etree.ElementTree as ET
import os
import subprocess

def run_clips_and_get_java(clips_file_path):
    import subprocess

    try:
        result = subprocess.run(
            ["clips", "-f2", clips_file_path], capture_output=True, text=True, check=True
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        return f"Error ejecutando CLIPS: {e}"
    
def process_xmi_to_clips(xmi_path, clips_output_path):
    classes, relationships = extract_classes_and_relationships(xmi_path)
    clips_facts = generate_clips_facts(classes, relationships)
    write_clips_file(clips_facts, clips_output_path)
    java_code = run_clips_and_get_java(clips_output_path)
    return java_code

def parse_xmi(file_path):
    tree = ET.parse(file_path)
    root = tree.getroot()
    print(f"Root element: {root.tag}")
    return root

def extract_classes_and_relationships(xmi_path):
    import xml.etree.ElementTree as ET

    tree = ET.parse(xmi_path)
    root = tree.getroot()

    ns = {
        'xmi': "http://schema.omg.org/spec/XMI/2.1",
        'uml': "http://www.omg.org/spec/UML/20090901"
    }

    classes = []
    relationships = []

    for elem in root.findall('.//packagedElement', ns):
        if elem.get('{http://schema.omg.org/spec/XMI/2.1}type') == 'uml:Class':
            class_name = elem.get('name')
            attributes = [attr.get('name') for attr in elem.findall('ownedAttribute', ns)]
            operations = [op.get('name') for op in elem.findall('ownedOperation', ns)]
            classes.append({'name': class_name, 'attributes': attributes, 'operations': operations})

        elif elem.get('{http://schema.omg.org/spec/XMI/2.1}type') in ['uml:Association', 'uml:Composition', 'uml:Aggregation']:
            relation_type = elem.get('{http://schema.omg.org/spec/XMI/2.1}type').split(':')[-1].lower()
            member_end = elem.get('memberEnd', '').split()
            if len(member_end) == 2:
                source, target = member_end
                multiplicity1 = elem.find('ownedEnd[@type="' + source + '"]', ns).get('lowerValue', '1') + '..' + \
                                elem.find('ownedEnd[@type="' + source + '"]', ns).get('upperValue', '*')
                multiplicity2 = elem.find('ownedEnd[@type="' + target + '"]', ns).get('lowerValue', '1') + '..' + \
                                elem.find('ownedEnd[@type="' + target + '"]', ns).get('upperValue', '*')

                relationships.append({'type': relation_type, 'from': source, 'to': target, 
                                      'multiplicity1': multiplicity1, 'multiplicity2': multiplicity2})

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

    # Plantillas para clases
    clips_facts.append('(deftemplate class (slot name) (multislot attributes) (multislot operations))')

    # Plantillas para relaciones nuevas
    clips_facts.append('(deftemplate association (slot source) (slot target) (multiplicity1) (multiplicity2))')
    clips_facts.append('(deftemplate composition (slot whole) (slot part) (multiplicity))')
    clips_facts.append('(deftemplate aggregation (slot whole) (slot part) (multiplicity))')

    # Generar hechos para clases
    for cls in classes:
        attributes = ' '.join([f'"{attr}"' for attr in cls['attributes']])
        operations = ' '.join([f'"{op}"' for op in cls['operations']])
        clips_facts.append(f'(class (name "{cls["name"]}") (attributes {attributes}) (operations {operations}))')

    # Generar hechos para relaciones
    for rel in relationships:
        if rel['type'] == 'asociación':
            clips_facts.append(f'(association (source "{rel["from"]}") (target "{rel["to"]}") '
                               f'(multiplicity1 "{rel["multiplicity1"]}") (multiplicity2 "{rel["multiplicity2"]}"))')
        elif rel['type'] == 'composición':
            clips_facts.append(f'(composition (whole "{rel["from"]}") (part "{rel["to"]}") '
                               f'(multiplicity "{rel["multiplicity1"]}"))')
        elif rel['type'] == 'agregación':
            clips_facts.append(f'(aggregation (whole "{rel["from"]}") (part "{rel["to"]}") '
                               f'(multiplicity "{rel["multiplicity1"]}"))')

    return clips_facts

def write_clips_file(clips_facts, file_path):
    with open(file_path, 'w') as file:
        for fact in clips_facts:
            file.write(f'{fact}\n')

        # Reglas CLIPS para generación de código Java
        file.write('''
        (defrule generate-java-code-association
            ?assoc <- (association (source ?source) (target ?target) (multiplicity1 ?m1) (multiplicity2 ?m2))
            =>
            (printout t "// Asociación entre " ?source " y " ?target crlf)
            (printout t "class " ?source " {" crlf)
            (printout t "   ArrayList<" ?target "> relaciones;" crlf "}" crlf)
        )

        (defrule generate-java-code-composition
            ?comp <- (composition (whole ?whole) (part ?part) (multiplicity ?m))
            =>
            (printout t "// Composición entre " ?whole " y " ?part crlf)
            (printout t "class " ?whole " {" crlf)
            (printout t "   TreeSet<" ?part "> partes;" crlf "}" crlf)
        )

        (defrule generate-java-code-aggregation
            ?agg <- (aggregation (whole ?whole) (part ?part) (multiplicity ?m))
            =>
            (printout t "// Agregación entre " ?whole " y " ?part crlf)
            (printout t "class " ?whole " {" crlf)
            (printout t "   LinkedList<" ?part "> partes;" crlf "}" crlf)
        )
        ''')

##############################################################################            

# # Abre el archivo en modo lectura
# xmi_file_path = 'generated/xmi/diagram.xmi'

# if os.path.exists(xmi_file_path):
#     with open(xmi_file_path, 'r') as archivo:
#         xmi_data = archivo.read()
# else:
#     print(f"Error: No se encontró el archivo {xmi_file_path}")

# # Archivo de salida CLIPS
# clips_file = 'output.clp'

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
