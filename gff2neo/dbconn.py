"""
Interface to the Neo4j Database
"""
import sys

from tqdm import tqdm

from model.core import *
from ncbi import fetch_publication_list
from py2neo import Graph, getenv, watch
from quickgo import fetch_quick_go_data
from uniprot import *

graph = Graph(host=getenv("DB", "localhost"), bolt=True,
              password=getenv("NEO4J_PASSWORD", ""))

# watch("neo4j.bolt")

gene_dict = dict()
transcript_dict = dict()
pseudogene_dict = dict()
cds_dict = dict()
exon_dict = dict()
rrna_dict = dict()
trna_dict = dict()
ncrna_dict = dict()
location_dict = dict()


def delete_data():
    """
    Delete existing data.
    :return:
    """
    # print("Deleting all nodes and relationships in {}".format(graph))
    sys.stdout.write("Deleting all nodes and relationships in {}".format(graph))

    graph.delete_all()


def create_organism_nodes():
    """
    Create Organism Nodes
    :return:
    """
    abbrev = "H37Rv"
    strain = abbrev
    genus = "Mycobacterium"
    species = "M. tuberculosis"
    common_name = "TB"

    organism = Organism(abbreviation=abbrev, strain=strain, genus=genus,
                        species=species, common_name=common_name)
    graph.create(organism)


def create_chromosome_nodes():
    """
    Create Chromosome Nodes
    :return:
    """
    name = "Chr1"
    uniquename = "Chr1"
    chromosome = Chromosome()
    chromosome.name = name
    chromosome.uniquename = uniquename
    graph.create(chromosome)


def create_gene_nodes(feature):
    """
    Create Gene Nodes
    :param feature:
    :return:
    """
    names = get_feature_name(feature)
    name = names.get("Name", names.get("UniqueName"))
    unique_name = names.get("UniqueName", name)
    description = feature.qualifiers["description"]
    biotype = feature.qualifiers['biotype'][0]
    parent = get_feature_parent(feature)

    gene = Gene()
    gene.name = name
    gene.uniquename = unique_name
    gene.parent = parent
    gene.biotype = biotype
    gene.description = description
    graph.create(gene)
    gene_dict[unique_name] = gene


def create_transcript_nodes(feature):
    """
    Create Transcipt Nodes
    :param feature:
    :return:
    """
    names = get_feature_name(feature)
    name = names.get("Name", names.get("UniqueName"))
    unique_name = names.get("UniqueName", name)
    biotype = feature.qualifiers['biotype'][0]
    parent = get_feature_parent(feature)

    transcript = Transcript()
    transcript.name = name
    transcript.parent = parent
    transcript.uniquename = unique_name
    transcript.biotype = biotype
    graph.create(transcript)
    transcript_dict[unique_name] = transcript


def create_pseudogene_nodes(feature):
    """
    Create Pseudogene Nodes
    :param feature:
    :return:
    """
    names = get_feature_name(feature)
    name = names.get("Name", names.get("UniqueName"))
    unique_name = names.get("UniqueName", name)
    description = feature.qualifiers["description"][0]
    biotype = feature.qualifiers['biotype'][0]
    parent = get_feature_parent(feature)

    pseudogene = PseudoGene()
    pseudogene.name = name
    pseudogene.uniquename = unique_name
    pseudogene.parent = parent
    pseudogene.description = description
    pseudogene.biotype = biotype
    graph.create(pseudogene)
    pseudogene_dict[unique_name] = pseudogene


def create_exon_nodes(feature):
    """
    Create Exon Nodes
    :param feature:
    :return:
    """
    names = get_feature_name(feature)
    name = names.get("Name", names.get("UniqueName"))
    unique_name = names.get("UniqueName", name)
    parent = get_feature_parent(feature)

    exon = Exon()
    exon.name = name
    exon.uniquename = unique_name
    exon.parent = parent
    graph.create(exon)
    exon_dict[unique_name] = exon


def create_rna_nodes(feature):
    """
    Create RNA Nodes
    :param feature:
    :return:
    """
    names = get_feature_name(feature)
    name = names.get("Name", names.get("UniqueName"))
    unique_name = names.get("UniqueName", name)
    parent = get_feature_parent(feature)

    if feature.type == 'tRNA_gene':
        trna = TRna()
        trna.name = name
        trna.parent = parent
        trna.uniquename = unique_name
        graph.create(trna)
        trna_dict[unique_name] = trna
    if feature.type == 'ncRNA_gene':
        ncrna = NCRna()
        ncrna.name = name
        ncrna.parent = parent
        ncrna.uniquename = unique_name
        graph.create(ncrna)
        ncrna_dict[unique_name] = ncrna
    if feature.type == 'rRNA_gene':
        rrna = RRna()
        rrna.name = name
        rrna.parent = parent
        rrna.uniquename = unique_name
        graph.create(rrna)
        rrna_dict[unique_name] = rrna


def create_cds_nodes(feature):
    """
    Create CDS Nodes
    :param feature:
    :return:
    """
    names = get_feature_name(feature)
    name = names.get("Name", names.get("UniqueName"))
    unique_name = names.get("UniqueName", name)
    parent = get_feature_parent(feature)

    cds = CDS()
    cds.name = name
    cds.parent = parent
    cds.uniquename = unique_name
    graph.create(cds)
    cds_dict[unique_name] = cds


def get_feature_parent(feature):
    if feature.qualifiers.get('Parent'):
        parent = feature.qualifiers['Parent'][0]
        # [feature.qualifiers['Parent'][0].find(":") + 1:]
    else:
        parent = None
    return parent


def create_featureloc_nodes(feature):
    """
    Create FeatureLoc Nodes
    :param feature:
    :return:
    """
    srcfeature_id = get_feature_name(feature).get("UniqueName")
    pk = feature.location.start + feature.location.end
    feature_loc = Location(pk=pk, fmin=feature.location.start, fmax=feature.location.end,
                           strand=feature.location.strand)
    graph.create(feature_loc)
    location_dict[srcfeature_id] = feature_loc


def get_feature_name(feature):
    """
    Get Feature Name and UniqueName
    :param feature:
    :return:
    """
    names = dict()
    if feature.qualifiers.get("Name"):
        names["Name"] = feature.qualifiers["Name"][0]
        names["UniqueName"] = feature.id
        # [feature.id.find(":") + 1:]
    else:
        names["Name"] = names["UniqueName"] = feature.id
        # [feature.id.find(":") + 1:]
    return names


def build_relationships():
    """
    Build relationships
    :return:
    """
    # TODO: Try optimize this
    print("\nBuilding Relationships...")
    for t, transcript in transcript_dict.iteritems():
        if transcript.parent in gene_dict.keys():
            gene = gene_dict.get(transcript.parent)
            transcript.part_of_g.add(gene)
            graph.push(transcript)
        for g, gene in gene_dict.iteritems():
            if transcript.parent == gene.uniquename:
                transcript.part_of_g.add(gene)
                graph.push(transcript)
        for p, pseudogene in pseudogene_dict.iteritems():
            if transcript.parent == pseudogene.uniquename:
                transcript.part_of_pg.add(pseudogene)
                graph.push(transcript)
        for c, cds in cds_dict.iteritems():
            if transcript.parent == cds.uniquename:
                cds.part_of.add(transcript)
                graph.push(cds)


def map_to_location(feature):
    # Find feature location with a srcfeature_id attr. matching this features uniquename and link them via
    # LOCATED_AT
    srcfeature_id = get_feature_name(feature).get("UniqueName")
    location = location_dict.get(srcfeature_id)
    organism = Organism.select(graph).first()
    chromosome = Chromosome.select(graph).first()
    rna = ["tRNA_gene", "ncRNA_gene", "rRNA_gene"]
    if location:
        if feature.type == 'gene':
            _feature = gene_dict.get(srcfeature_id)
            _feature.location.add(location)
            _feature.belongs_to.add(organism)
            _feature.located_on.add(chromosome)
            graph.push(_feature)
        elif feature.type == 'pseudogene':
            _feature = pseudogene_dict.get(srcfeature_id)
            _feature.location.add(location)
            _feature.belongs_to.add(organism)
            _feature.located_on.add(chromosome)
            graph.push(_feature)
        elif feature.type == 'exon':
            _feature = exon_dict.get(srcfeature_id)
            _feature.location.add(location)
            _feature.belongs_to.add(organism)
            _feature.located_on.add(chromosome)
            graph.push(_feature)
        elif feature.type in rna:
            if feature.type == 'tRNA_gene':
                _feature = trna_dict.get(srcfeature_id)
                _feature.location.add(location)
                _feature.belongs_to.add(organism)
                _feature.located_on.add(chromosome)
                graph.push(_feature)
            if feature.type == 'ncRNA_gene':
                _feature = ncrna_dict.get(srcfeature_id)
                _feature.location.add(location)
                _feature.belongs_to.add(organism)
                _feature.located_on.add(chromosome)
                graph.push(_feature)
            if feature.type == 'rRNA_gene':
                _feature = rrna_dict.get(srcfeature_id)
                _feature.location.add(location)
                _feature.belongs_to.add(organism)
                _feature.located_on.add(chromosome)
                graph.push(_feature)
        elif feature.type == 'CDS':
            _feature = cds_dict.get(srcfeature_id)
            _feature.location.add(location)
            _feature.belongs_to.add(organism)
            _feature.located_on.add(chromosome)
            graph.push(_feature)
        elif feature.type == 'transcript':
            _feature = transcript_dict.get(srcfeature_id)
            _feature.location.add(location)
            _feature.belongs_to.add(organism)
            _feature.located_on.add(chromosome)
            graph.push(_feature)


def create_cv_term_nodes(Protein, bp, cc, mf):
    """
    Create CvTerm Nodes and build Polypetide relationships.
    :param Protein:
    :param bp:
    :param cc:
    :param mf:
    :return:
    """
    # go(biological process)
    go_bp_ids = [t[t.find('G'):-1] for t in bp.split('; ') if t is not '']
    go_bp_defs = [t[:t.find('[') - 1] for t in bp.split('; ') if t is not '']
    # go(cellular component)
    go_cc_ids = [t[t.find('G'):-1] for t in cc.split('; ') if t is not '']
    go_cc_defs = [t[:t.find('[') - 1] for t in cc.split('; ') if t is not '']
    # go(molecular function)
    go_mf_ids = [t[t.find('G'):-1] for t in mf.split('; ') if t is not '']
    go_mf_defs = [t[:t.find('[') - 1] for t in mf.split('; ') if t is not '']

    # TODO: Find a way to refactor this.
    for _id in go_bp_ids:
        cv = GOTerm()
        for _def in go_bp_defs:
            cv.name = _id
            cv.definition = _def
            cv.namespace = "biological process"
            graph.create(cv)
            Protein.cvterm.add(cv)
            graph.push(Protein)

    for _id in go_mf_ids:
        cv = GOTerm()
        for _def in go_mf_defs:
            cv.name = _id
            cv.definition = _def
            cv.namespace = "cellular component"
            graph.create(cv)
            Protein.cvterm.add(cv)
            graph.push(Protein)
    for _id in go_cc_ids:
        cv = GOTerm()
        for _def in go_cc_defs:
            cv.name = _id
            cv.definition = _def
            cv.namespace = "molecular function"
            graph.create(cv)
            Protein.cvterm.add(cv)
            graph.push(Protein)


def create_interpro_term_nodes(Protein, entry):
    """
    Create InterPro Term Nodes.
    :param Protein:
    :param entry:
    :return:
    """
    # http://generic-model-organism-system-database.450254.n5.nabble.com/Re-GMOD-devel-Storing-Interpro-domains-in-Chado-td459778.html
    terms = [t for t in entry.split("; ") if t is not '']
    for interpro in terms:
        import time
        dbxref = DbXref(db="InterPro", accession=interpro, version=time.time())
        graph.create(dbxref)
        Protein.dbxref.add(dbxref)
        graph.push(Protein)


def create_author_nodes(publication, full_author):
    """
    Create Author Nodes.
    :param publication:
    :param full_author:
    :return:
    """
    # TODO: Get more info about Authors
    if full_author:
        for au in full_author:
            _author = Author()
            _author.givennames = au
            graph.create(_author)
            _author.wrote.add(publication)
            publication.author.add(_author)
            graph.push(_author)
            graph.push(publication)


# TODO: Fetch data from PubMed

def update_pub_nodes():
    publications = Publication.select(graph)
    print(len(list(publications)))
    pmids = [publication.pmid for publication in publications]
    publication_by_id = dict(zip(pmids, publications))
    num_ids = len(pmids)
    chunksize = 500
    records = []
    for start in range(0, num_ids, chunksize):
        subset = pmids[start:start + chunksize]
        records.extend(fetch_publication_list(subset))
    record_loaded_count = 0
    for record in records:
        if len(record) < 2:
            pm_id = record['id:'][0][record['id:'][0].find('able: ') + 6:]
            print("PMID: {}".format(pm_id))
            record = fetch_publication_list(pm_id, rettype='xml')
            rec = next(record)
            article = rec['MedlineCitation']['Article']
            title = article['ArticleTitle']
            pages = article['Pagination']['MedlinePgn']
            volume = article['Journal']['JournalIssue']['Volume']
            issue = article['Journal']['JournalIssue']['Issue']
            date_of_pub = article['Journal']['JournalIssue']['PubDate']['Month'] + " " + \
                          article['Journal']['JournalIssue']['PubDate']['Year']
            pub_place = rec['MedlineCitation']['MedlineJournalInfo']['Country']
            publisher = None
            author = None
            # full_author = article['AuthorList']
            full_author = None
        else:
            # https://www.nlm.nih.gov/bsd/mms/medlineelements.html
            pm_id = record['PMID']
            # there is internal caching so using a dictionary here doesn't
            # actually seem to save any time - pvh
            title = record.get('TI', None)
            volume = record.get('VI', None)
            issue = record.get('IP', None)
            pages = record.get('PG', None)
            date_of_pub = record.get('DP', None)
            pub_place = record.get('PL', None)
            publisher = record.get('SO', None)
            author = record.get('AU', None)
            full_author = record.get('FAU', None)

        # Publication.select(graph, pm_id).first()
        publication = publication_by_id[pm_id]
        publication.title = title
        publication.volume = volume
        publication.issue = issue
        publication.pages = pages
        publication.year = date_of_pub
        publication.pubplace = pub_place
        publication.publisher = publisher
        graph.push(publication)
        create_author_nodes(publication, full_author)
        record_loaded_count += 1


def create_pub_nodes(Protein, pubs):
    """
    Create Publication Nodes
    :param Protein:
    :param pubs:
    :return:
    """
    citations = [c for c in pubs.split("; ") if c is not '']

    for citation in citations:
        pub = Publication()
        pub.pmid = citation

        Protein.published_in.add(pub)
        graph.push(Protein)


def create_is_a_cv_term_rel():
    """
    Creating IS_A relationships between CVTerms
    :return:
    """
    cv_terms = GOTerm.select(graph)
    for cv in cv_terms:
        is_a_list = fetch_quick_go_data(cv.name)
        # cv = CvTerm.select(graph, _id).first()
        for go in is_a_list:
            goid = go[go.find('G'):go.find('!')].strip()
            cv_term = GOTerm.select(graph, goid).first()
            if cv_term:
                cv.is_a.add(cv_term)
                graph.push(cv)


def build_protein_interaction_rels(protein_interaction_dict):
    """
    Build protein-protein interactions
    :param protein_interaction_dict:
    :return:
    """
    for uni_id, interactors in protein_interaction_dict.items():
        if len(interactors) > 0:
            poly = Protein.select(graph, uni_id).first()
            interactors = interactors.split('; ')
            for interactor in interactors:
                if interactor == 'Itself':
                    interactor = poly.uniquename
                _poly = Protein.select(graph, interactor).first()
                if _poly is None:
                    print("No Protein with uniquename: {}".format(interactor))
                    # time.sleep(2)
                else:
                    poly.interacts_with.add(_poly)
                    graph.push(poly)


def create_uniprot_nodes(uniprot_data):
    """
    Build DbXref nodes from UniProt results.
    :param uniprot_data:
    :return:
    """
    print("=========================================")
    print("About to create Nodes from UniProt data.")
    print("=========================================")
    # time.sleep(2)
    count = 0
    protein_interaction_dict = dict()
    for entry in uniprot_data:
        protein_interaction_dict[entry[0]] = entry[6]
        count += 1

        dbxref = DbXref(db="UniProt", accession=entry[1], version=entry[0])
        graph.create(dbxref)
        pdb_id = map_ue_to_pdb(entry[0])
        Protein = Protein()
        Protein.name = entry[9]
        Protein.uniquename = entry[0]
        Protein.ontology_id = Protein.so_id
        Protein.seqlen = entry[16]
        Protein.residues = entry[14]
        Protein.parent = entry[2]
        Protein.family = entry[17]
        Protein.function = entry[13]
        Protein.pdb_id = pdb_id
        Protein.mass = entry[15]
        Protein.three_d = entry[12]
        graph.create(Protein)

        gene = Gene.select(graph, "gene:" + entry[2]).first()
        if gene:
            _feature = Feature.select(graph).where(
                "_.parent = '{}'".format(gene.uniquename)).first()
            if _feature:
                transcript = Transcript.select(
                    graph, _feature.uniquename).first()
                if transcript:
                    cds = CDS.select(
                        graph, "CDS" + transcript.uniquename[transcript.uniquename.find(":"):]).first()
                    if cds:
                        # Polypetide-derives_from->CDS
                        Protein.derives_from.add(cds)
                        cds.Protein.add(Protein)
                        graph.push(Protein)
                        graph.push(cds)

        Protein.dbxref.add(dbxref)
        graph.push(Protein)

        create_cv_term_nodes(Protein, entry[18], entry[19], entry[20])
        create_interpro_term_nodes(Protein, entry[5])
        create_pub_nodes(Protein, entry[11])
    build_protein_interaction_rels(protein_interaction_dict)
    print ("TOTAL:", count)