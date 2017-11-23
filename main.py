#!/usr/bin/env python
from gff2neo.gffproc import *

gff_file = "data/MTB_H37rv.gff3"


def check_csv(csvfile):
    """
    Check if csv file exists and is not empty
    :param csvfile:
    :return:
    """
    _file = False
    if os.path.exists(csvfile) and os.stat(csvfile).st_size > 0:
        _file = True
    return _file


def main():
    if os.path.isdir(os.getcwd() + "/data") and os.path.exists(gff_file):
        import time
        time.sleep(20)
        delete_data()
        examine(gff_file)
        gff_p_st = time.time()
        parse_gff(gff_file)
        gff_p_end = time.time()
        sys.stdout.write("\nDone parsing GFF in {} seconds.\n".format(gff_p_end - gff_p_st))
        rel_st = time.time()
        build_gff_rels()
        rel_end = time.time()
        sys.stdout.write("\nBuilt GFF relationships in {} seconds.\n".format(rel_end - rel_st))
        if check_csv(uniprot_data_csv):
            create_uniprot_nodes()
            create_kegg_pathways()
            create_pathway_nodes()
            create_go_term_nodes()
            if check_csv(target_protein_ids_csv) and check_csv(drug_vocab_csv):
                create_drugbank_nodes()
            create_pub_nodes()
            map_gene_protein(get_locus_tags(gff_file, 400))
        else:
            query_uniprot(get_locus_tags(gff_file, 400))
            create_uniprot_nodes()
            create_kegg_pathways()
            create_pathway_nodes()
            create_go_term_nodes()
            if check_csv(target_protein_ids_csv) and check_csv(drug_vocab_csv):
                create_drugbank_nodes()
            create_pub_nodes()
            map_gene_protein(get_locus_tags(gff_file, 400))
    else:
        raise Exception("Couldn't find H37Rv GFF file: {}!".format(gff_file))


if __name__ == '__main__':
    main()
