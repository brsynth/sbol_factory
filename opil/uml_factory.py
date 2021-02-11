import sbol3 as sbol
from sbol3 import set_namespace
from sbol3 import CombinatorialDerivation, Component, Measure, VariableFeature
# pySBOL extension classes are aliased because they are not present in SBOL-OWL
from sbol3 import CustomTopLevel as TopLevel
from sbol3 import CustomIdentified as Identified
import graphviz

import rdflib
import os
import posixpath
#import logging
from math import inf

class OPILFactory():

    __doc__ = ''  # Documentation string

    @staticmethod
    def make_qname(class_uri):
        class_name = sbol.utils.parse_class_name(class_uri)
        prefix = ''
        if str(Query.SBOL) in class_uri:
            prefix = 'sbol:'
        elif str(Query.OM) in class_uri:
            prefix = 'om:'
        qname = prefix + class_name
        return qname

    @staticmethod
    def create_uml_record(dot_graph, class_uri, label):
        class_name = sbol.utils.parse_class_name(class_uri)
        node_format = {
            'label' : None,
            'fontname' : 'Bitstream Vera Sans',
            'fontsize' : '8',
            'shape': 'record'
            }
        node_format['label'] = label
        dot_graph.node(class_name, **node_format)

    @staticmethod
    def create_association(dot_graph, subject_uri, object_uri, label):
        subject_class = sbol.utils.parse_class_name(subject_uri)
        object_class = sbol.utils.parse_class_name(object_uri)
        association_relationship = {
                'label' : None,
                'arrowtail' : 'odiamond',
                'arrowhead' : 'vee',
                'fontname' : 'Bitstream Vera Sans',
                'fontsize' : '8',
                'dir' : 'both'
            } 
        association_relationship['label'] = label
        dot_graph.edge(subject_class, object_class, **association_relationship)
        qname = OPILFactory.make_qname(object_uri)
        label = '{' + qname + '|}'
        OPILFactory.create_uml_record(dot_graph, object_uri, label)

    def create_composition(dot_graph, subject_uri, object_uri, label):
        subject_class = sbol.utils.parse_class_name(subject_uri)
        object_class = sbol.utils.parse_class_name(object_uri)
        composition_relationship = {
                'label' : None,
                'arrowtail' : 'diamond',
                'arrowhead' : 'vee',
                'fontname' : 'Bitstream Vera Sans',
                'fontsize' : '8',
                'dir' : 'both'
            } 
        composition_relationship['label'] = label
        dot_graph.edge(subject_class, object_class, **composition_relationship)
        qname = OPILFactory.make_qname(object_uri)
        label = '{' + qname + '|}'
        OPILFactory.create_uml_record(dot_graph, object_uri, label)

    def create_inheritance(dot_graph, superclass_uri, subclass_uri):
        superclass = sbol.utils.parse_class_name(superclass_uri)
        subclass = sbol.utils.parse_class_name(subclass_uri)
        inheritance_relationship = {
                'label' : None,
                'arrowtail' : 'empty',
                'fontname' : 'Bitstream Vera Sans',
                'fontsize' : '8',
                'dir' : 'back'
            } 
        dot_graph.edge(superclass, subclass, **inheritance_relationship)
        qname = OPILFactory.make_qname(superclass_uri)
        label = '{' + qname + '|}'
        OPILFactory.create_uml_record(dot_graph, superclass_uri, label)

    @staticmethod
    def generate(class_uri, drawing_method_callback, dot_graph=None):
        if Query.OPIL not in class_uri:
            return ''
        superclass_uri = Query.query_superclass(class_uri)
        OPILFactory.generate(superclass_uri, drawing_method_callback, dot_graph)

        class_name = sbol.utils.parse_class_name(class_uri)

        if class_name in globals().keys():
            return ''

        drawing_method_callback(class_uri, superclass_uri, dot_graph)

    @staticmethod
    def draw_abstraction_hierarchy(class_uri, superclass_uri, dot_graph=None):

        subclass_uris = Query.query_subclasses(class_uri)
        if len(subclass_uris) <= 1:
            return 

        class_name = sbol.utils.parse_class_name(class_uri)
        if dot_graph:
            dot = dot_graph
        else:
            dot = graphviz.Digraph(class_name)

        qname = OPILFactory.make_qname(class_uri)
        label = f'{qname}|'
        label = '{' + label + '}'  # graphviz syntax for record-style label
        OPILFactory.create_uml_record(dot, class_uri, label)

        for uri in subclass_uris:
            subclass_name = sbol.utils.parse_class_name(uri)
            OPILFactory.create_inheritance(dot, class_uri, uri)
            #label = f'{subclass_name}|'
            #label = '{' + label + '}'  # graphviz syntax for record-style label
            label = OPILFactory.label_properties(uri)
            OPILFactory.create_uml_record(dot, uri, label)

        if not dot_graph:
            source = graphviz.Source(dot.source.replace('\\\\', '\\'))
            source.render(f'./uml/{class_name}_abstraction_hierarchy')
        return

    @staticmethod
    def label_properties(class_uri):
        class_name = sbol.utils.parse_class_name(class_uri)
        qname = OPILFactory.make_qname(class_uri)
        label = f'{qname}|'

        # Object properties can be either compositional or associative
        property_uris = Query.query_object_properties(class_uri)
        compositional_properties = Query.query_compositional_properties(class_uri)
        associative_properties = [uri for uri in property_uris if uri not in
                                    compositional_properties]

        # Initialize associative properties
        for property_uri in associative_properties:
            if len(associative_properties) != len(set(associative_properties)):
                print(f'{property_uri} is found more than once')
            property_name = Query.query_label(property_uri).replace(' ', '_')
            property_name = OPILFactory.make_qname(property_uri)
            lower_bound, upper_bound = Query.query_cardinality(property_uri, class_uri)
            if upper_bound == inf:
                upper_bound = '*'
            object_class_uri = Query.query_range(property_uri)
            arrow_label = f'{property_name} [{lower_bound}..{upper_bound}]'
            OPILFactory.create_association(dot, class_uri, object_class_uri, arrow_label)
            # self.__dict__[property_name] = sbol.ReferencedObject(self, property_uri, 0, upper_bound)

        # Initialize compositional properties
        for property_uri in compositional_properties:
            if len(compositional_properties) != len(set(compositional_properties)):
                print(f'{property_uri} is found more than once')
            property_name = Query.query_label(property_uri).replace(' ', '_')
            property_name = OPILFactory.make_qname(property_uri)
            cardinality = Query.query_cardinality(property_uri, class_uri)
            lower_bound, upper_bound = Query.query_cardinality(property_uri, class_uri)
            if upper_bound == inf:
                upper_bound = '*'
            object_class_uri = Query.query_range(property_uri)
            arrow_label = f'{property_name} [{lower_bound}..{upper_bound}]'
            OPILFactory.create_composition(dot, class_uri, object_class_uri, arrow_label)

        # Initialize datatype properties
        property_uris = Query.query_datatype_properties(class_uri)
        for property_uri in property_uris:
            property_name = Query.query_label(property_uri).replace(' ', '_')
            property_name = OPILFactory.make_qname(property_uri)

            # Get the datatype of this property
            datatypes = Query.query_property_datatype(property_uri, class_uri)
            if len(datatypes) == 0:
                continue
            if len(datatypes) > 1:  # This might indicate an error in the ontology
                raise
            # Get the cardinality of this datatype property
            lower_bound, upper_bound = Query.query_cardinality(property_uri, class_uri)
            if upper_bound == inf:
                upper_bound = '*'
            datatype = sbol.utils.parse_class_name(datatypes[0])
            if datatype == 'anyURI':
                datatype = 'URI'
            label += f'{property_name} [{lower_bound}..{upper_bound}]: {datatype}\\l'
        label = '{' + label + '}'  # graphviz syntax for record-style label
        return label

    @staticmethod
    def draw_class_definition(class_uri, superclass_uri, dot_graph=None):

        CLASS_URI = class_uri
        CLASS_NAME = sbol.utils.parse_class_name(class_uri)
        SUPERCLASS_NAME = sbol.utils.parse_class_name(superclass_uri)

        log = ''
        prefix = ''
        qname = OPILFactory.make_qname(class_uri)
        label = f'{qname}|'

        if dot_graph:
            dot = dot_graph
        else:
            dot = graphviz.Digraph(CLASS_NAME)

        OPILFactory.create_inheritance(dot, superclass_uri, class_uri)

        # Object properties can be either compositional or associative
        property_uris = Query.query_object_properties(CLASS_URI)
        compositional_properties = Query.query_compositional_properties(CLASS_URI)
        associative_properties = [uri for uri in property_uris if uri not in
                                    compositional_properties]

        # Initialize associative properties
        for property_uri in associative_properties:
            if len(associative_properties) != len(set(associative_properties)):
                print(f'{property_uri} is found more than once')
            property_name = Query.query_label(property_uri).replace(' ', '_')
            property_name = OPILFactory.make_qname(property_uri)
            lower_bound, upper_bound = Query.query_cardinality(property_uri, class_uri)
            if upper_bound == inf:
                upper_bound = '*'
            object_class_uri = Query.query_property_datatype(property_uri, CLASS_URI)[0]
            arrow_label = f'{property_name} [{lower_bound}..{upper_bound}]'
            OPILFactory.create_association(dot, class_uri, object_class_uri, arrow_label)
            # self.__dict__[property_name] = sbol.ReferencedObject(self, property_uri, 0, upper_bound)

        # Initialize compositional properties
        for property_uri in compositional_properties:
            if len(compositional_properties) != len(set(compositional_properties)):
                print(f'{property_uri} is found more than once')
            property_name = Query.query_label(property_uri).replace(' ', '_')
            property_name = OPILFactory.make_qname(property_uri)
            lower_bound, upper_bound = Query.query_cardinality(property_uri, class_uri)
            if upper_bound == inf:
                upper_bound = '*'
            object_class_uri = Query.query_property_datatype(property_uri, CLASS_URI)[0]
            arrow_label = f'{property_name} [{lower_bound}..{upper_bound}]'
            OPILFactory.create_composition(dot, class_uri, object_class_uri, arrow_label)

        # Initialize datatype properties
        property_uris = Query.query_datatype_properties(CLASS_URI)
        for property_uri in property_uris:
            property_name = Query.query_label(property_uri).replace(' ', '_')
            property_name = OPILFactory.make_qname(property_uri)
            
            # Get the datatype of this property
            datatypes = Query.query_property_datatype(property_uri, CLASS_URI)
            if len(datatypes) == 0:
                continue
            if len(datatypes) > 1:  # This might indicate an error in the ontology
                raise
            # Get the cardinality of this datatype property
            lower_bound, upper_bound = Query.query_cardinality(property_uri, class_uri)
            if upper_bound == inf:
                upper_bound = '*'

            datatype = sbol.utils.parse_class_name(datatypes[0])
            if datatype == 'anyURI':
                datatype = 'URI'
            label += f'{property_name} [{lower_bound}..{upper_bound}]: {datatype}\\l'
        label = '{' + label + '}'  # graphviz syntax for record-style label
        OPILFactory.create_uml_record(dot, class_uri, label)
        if not dot_graph:
            source = graphviz.Source(dot.source.replace('\\\\', '\\'))
            source.render(f'./uml/{CLASS_NAME}')
        return log

class Query():
    filename='sbol.rdf'
    OWL = rdflib.URIRef('http://www.w3.org/2002/07/owl#')
    RDF = rdflib.URIRef('http://www.w3.org/1999/02/22-rdf-syntax-ns#')
    SBOL = rdflib.URIRef('http://sbols.org/v3#')
    OPIL = rdflib.URIRef('http://bioprotocols.org/opil/v1#')
    OM = rdflib.URIRef('http://www.ontology-of-units-of-measure.org/resource/om-2/')

    graph = rdflib.Graph()
    graph.parse(posixpath.join(os.path.dirname(os.path.realpath(__file__)), 'rdf/opil.ttl'), format ='ttl')
    graph.parse(posixpath.join(os.path.dirname(os.path.realpath(__file__)), 'rdf/sbol3.ttl'), format ='ttl')
    graph.namespace_manager.bind('sbol', SBOL)
    graph.namespace_manager.bind('opil', OPIL)
    graph.namespace_manager.bind('tawny', rdflib.URIRef('http://www.purl.org/ontolink/tawny#'))
    graph.namespace_manager.bind('owl', rdflib.URIRef('http://www.w3.org/2002/07/owl#'))
    graph.namespace_manager.bind('rdfs', rdflib.URIRef('http://www.w3.org/2000/01/rdf-schema#'))
    graph.namespace_manager.bind('rdf', rdflib.URIRef('http://www.w3.org/1999/02/22-rdf-syntax-ns#'))
    graph.namespace_manager.bind('xsd', rdflib.URIRef('http://www.w3.org/2001/XMLSchema#'))

    # for s in graph.subjects(RDF + rdflib.URIRef('type'), OWL + rdflib.URIRef('Class')):
    #     logging.info(s)

    prefixes = '''PREFIX sbol: <http://sbols.org/v2#>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX owl: <http://www.w3.org/2002/07/owl#>
    PREFIX tawny: <http://www.purl.org/ontolink/tawny#>
    PREFIX xml: <http://www.w3.org/XML/1998/namespace>
    PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#">
    '''

    def query_base_class(cls):
        try:
            superclass = Query.query_superclass(cls)
            return Query.query_base_class(superclass)
        except Exception as e:
            return cls

    @staticmethod
    def query_base_classes():
        class_list = Query.query_classes()
        base_classes = set()
        for cls in class_list:
            base_class = Query.query_base_class(cls)
            base_classes.add(base_class)
        return list(base_classes)

    @staticmethod
    def query_classes():
        query = '''
            SELECT distinct ?cls 
            WHERE 
            {{
                ?cls rdf:type owl:Class . 
            }}
            '''.format(str(Query.OPIL))
        response = Query.graph.query(query)
        sbol_types = [str(row[0]) for row in response]
        return sbol_types

    @staticmethod
    def query_subclasses(superclass):
        query = '''
            SELECT distinct ?subclass 
            WHERE 
            {{
                ?subclass rdf:type owl:Class .
                ?subclass rdfs:subClassOf <{}>
            }}
            '''.format(superclass)
        response = Query.graph.query(query)
        subclasses = [row[0] for row in response]
        return subclasses

    @staticmethod
    def query_superclass(subclass):
        query = '''
            SELECT distinct ?superclass 
            WHERE 
            {{
                ?superclass rdf:type owl:Class .
                <{}> rdfs:subClassOf ?superclass
            }}
            '''.format(subclass)
        response = Query.graph.query(query)
        if len(response) == 0:
            raise Exception('{} has no superclass'.format(subclass))
        if len(response) > 1:
            raise Exception('{} has more than one superclass'.format(subclass))
        for row in response:
            superclass = str(row[0])
        return superclass

    @staticmethod
    def query_object_properties(class_uri):
        query =     '''
            SELECT distinct ?property_uri
            WHERE 
            {{
                ?property_uri rdf:type owl:ObjectProperty .
                ?property_uri rdfs:domain/(owl:unionOf/rdf:rest*/rdf:first)* <{}>.
            }}
            '''.format(class_uri)
        response = Query.graph.query(query)
        response = [str(row[0]) for row in response]
        property_types = response

        # The type of inherited properties are sometimes overridden 
        query = '''
            SELECT distinct ?property_uri
            WHERE 
            {{
                ?property_uri rdf:type owl:ObjectProperty .
                <{}> rdfs:subClassOf ?restriction .
                ?restriction owl:onProperty ?property_uri .
            }}
            '''.format(class_uri) 
        response = Query.graph.query(query)
        response = [str(row[0]) for row in response]
        property_types.extend(response)
        return list(set(property_types))

    @staticmethod
    def query_compositional_properties(class_uri):
        query = '''
            SELECT distinct ?property_uri
            WHERE 
            {{
                ?property_uri rdf:type owl:ObjectProperty .
                ?property_uri rdfs:subPropertyOf opil:compositionalProperty .
                ?property_uri rdfs:domain/(owl:unionOf/rdf:rest*/rdf:first)* <{}>.
            }}
            '''.format(class_uri)

        response = Query.graph.query(query)
        response = [str(row[0]) for row in response]
        property_types = response

        # The type of inherited properties are sometimes overridden 
        query = '''
            SELECT distinct ?property_uri
            WHERE 
            {{
                ?property_uri rdf:type owl:ObjectProperty .
                ?property_uri rdfs:subPropertyOf opil:compositionalProperty .
                <{}> rdfs:subClassOf ?restriction .
                ?restriction owl:onProperty ?property_uri .
            }}
            '''.format(class_uri)
        response = Query.graph.query(query)
        response = [str(row[0]) for row in response]
        property_types.extend(response) 
        property_types = set(list(response))
        return property_types

    @staticmethod
    def query_datatype_properties(class_uri):
        query =     '''
            SELECT distinct ?property_uri
            WHERE 
            {{
                ?property_uri rdf:type owl:DatatypeProperty .
                ?property_uri rdfs:domain/(owl:unionOf/rdf:rest*/rdf:first)* <{}>.
            }}
            '''.format(class_uri)
        response = Query.graph.query(query)
        response = [str(row[0]) for row in response]
        property_types = response

        # The type of inherited properties are sometimes overridden 
        query = '''
            SELECT distinct ?property_uri
            WHERE 
            {{
                ?property_uri rdf:type owl:DatatypeProperty .
                <{}> rdfs:subClassOf ?restriction .
                ?restriction owl:onProperty ?property_uri .
            }}
            '''.format(class_uri) 
        response = Query.graph.query(query)
        response = [str(row[0]) for row in response]
        property_types.extend(response)
        return list(set(property_types))

    @staticmethod
    def query_cardinality(property_uri, class_uri):
        # The OPIL ontology does not explicitly specify cardinality restrictions
        # for every property, so some assumptions about defaults must be made
        lower_bound = 0
        upper_bound = inf
        query = '''
            SELECT distinct ?cardinality
            WHERE 
            {{{{
                <{}> rdfs:subClassOf ?restriction .
                ?restriction rdf:type owl:Restriction .
                ?restriction owl:onProperty <{}> .
                ?restriction {{}} ?cardinality .
            }}}}
            '''.format(class_uri, property_uri)
        response = Query.graph.query(query.format('owl:minCardinality'))
        response = [str(row[0]) for row in response]
        if len(response):
            lower_bound = int(response[0])
        response = Query.graph.query(query.format('owl:maxCardinality'))
        response = [str(row[0]) for row in response]
        if len(response):
            upper_bound = int(response[0])
        return (lower_bound, upper_bound)


    @staticmethod
    def query_property_datatype(property_uri, class_uri):
        # Check for a restriction first on a specific property of a specific class
        query = '''
            SELECT distinct ?datatype
            WHERE 
            {{
                <{}> rdfs:subClassOf ?restriction .
                ?restriction rdf:type owl:Restriction .
                ?restriction owl:allValuesFrom ?datatype .
                ?restriction owl:onProperty <{}> .
            }}
            '''.format(class_uri, property_uri)    
        response = Query.graph.query(query)
        response = [str(row[0]) for row in response]
        datatypes = response
        if len(datatypes) > 1:
            raise Exception(f'Conflicting owl:allValuesFrom restrictions found for values of {property_uri} property')
        if len(datatypes) == 1:
            return datatypes
        # If no restrictions are found, then search for ranges.
        # Ranges are more permissive, so more than one can range for a property can be found
        query = '''
            SELECT distinct ?datatype
            WHERE 
            {{
                <{}> rdfs:domain <{}> .
                <{}> rdfs:range ?datatype 
            }}
            '''.format(property_uri, class_uri, property_uri)    
        response = Query.graph.query(query)
        response = [str(row[0]) for row in response]
        if len(datatypes) > 1:
            raise Exception(f'Multiple ranges found for {property_uri} property. '
                            'Please specify owl:allValuesFrom restrictions for each domain class')
        datatypes = response
        return datatypes

    @staticmethod
    def query_label(property_uri):
        query =     '''
            SELECT distinct ?property_name
            WHERE 
            {{
                <{}> rdfs:label ?property_name
            }}
            '''.format(property_uri)    
        response = Query.graph.query(query)
        response = [str(row[0]) for row in response]
        if len(response) == 0:
            raise Exception(f'{property_uri} has no label')
        if len(response) > 1:
            raise Exception(f'{property_uri} has more than one label')
        property_name = response[0]
        return property_name

    @staticmethod
    def query_range(property_uri):
        query =     '''
            SELECT distinct ?object_class
            WHERE 
            {{
                <{}> rdfs:range ?object_class
            }}
            '''.format(property_uri)    
        response = Query.graph.query(query)
        response = [str(row[0]) for row in response]
        if len(response) == 0:
            raise Exception(f'{property_uri} has no range')
        if len(response) > 1:
            raise Exception(f'{property_uri} has more than one range')
        object_class = response[0]
        return object_class

log = ''
for class_uri in Query.query_classes():
    class_name = sbol.utils.parse_class_name(class_uri)
    dot = graphviz.Digraph(class_name)
    # dot.graph_attr['splines'] = 'ortho'
    OPILFactory.generate(class_uri, OPILFactory.draw_class_definition, dot)
    OPILFactory.generate(class_uri, OPILFactory.draw_abstraction_hierarchy, dot)
    source = graphviz.Source(dot.source.replace('\\\\', '\\'))
    source.render(f'./uml/{class_name}_definition_and_abstraction')


OPILFactory.__doc__ = log
