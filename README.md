<p align="center"><img src="extras/kaptive_logo.png" alt="Kaptive" width="400"></p>






## Welcome to the documentation page for Kaptive Web.

<b>Kaptive</b> reports information about capsular (K) loci found in genome assemblies.

Given a novel genome and a database of known K-loci, <b>Kaptive</b> will help you to decide whether your sample has a known or a novel K-locus. It carries out the following for each input genome assembly:
* BLAST for all known K-locus nucleotide sequences (using `blastn`) to identify the best match ('best' defined as having the highest coverage).
* Extract the region(s) of the assembly which correspond to the BLAST hits (i.e. the K-locus sequence in the assembly) and save it to a FASTA file.
* BLAST for all known K-locus genes (using `tblastn`) to identify which expected genes (genes in the best matching K-locus) are present/missing and whether any unexpected genes (genes from other K-loci) are present.
* Visualise the results on-screen in the form of images and tables.
* Summarise the results in downloadable table and json files.

<b>Kaptive</b> will indicate the confidence of the K-locus match.

In cases where your input assembly closely matches a known K-locus, <b>Kaptive</b> will indicate a "Perfect" or "Very High" confidence match. 

If <b>Kaptive</b> has lower confidence in the match it may mean that your assembly contains a novel K-locus, a deletion or an insertion sequence variant of a known locus. Alternatively it may mean that your input assembly was not of sufficient quality to make a confident match (e.g. if it is very fragmented).

<b>Kaptive</b> cannot reliably extract or annotate K-locus sequences for totally novel loci – if you think you have a novel K-locus you should investigate this further. If you think you may have a variant of a known locus, and you haven't already done so, you could try rerunning Kaptive with the appropriate variant database.  

If you do have a novel K-locus or novel variant and you would like it to be added to the database, [please let us know](https://github.com/kelwyres/Kaptive-Web/issues).

Read more about <b>Kaptive</b> and how it was used to classify K-loci in <i>Klebsiella</i> here:
[Wyres, K. et al. Identification of Klebsiella capsule synthesis loci from whole genome data. (2016) MGen 2, doi: 10.1099/mgen.0.000102](http://mgen.microbiologyresearch.org/content/journal/mgen/10.1099/mgen.0.000102)
Download the command-line version of <b>Kaptive</b> [here](https://github.com/katholt/kaptive) (enables advanced options). 

## Table of Contents

* [Input assemblies](https://github.com/kelwyres/Kaptive-Web#input-assemblies)
* [Results](https://github.com/kelwyres/Kaptive-Web#results)
* [Example results and interpretation](https://github.com/kelwyres/Kaptive-Web#example-results-and-interpretation)
  * [Very close match](https://github.com/kelwyres/Kaptive-Web#very-close-match)
  * [More distant match](https://github.com/kelwyres/Kaptive-Web#more-distant-match)
  * [Broken assembly](https://github.com/kelwyres/Kaptive-Web#broken-assembly)
  * [Poor match - possible novel locus](https://github.com/kelwyres/Kaptive-Web#poor-match---possible-novel-locus)
  * [Poor match - possible novel variant](https://github.com/kelwyres/Kaptive-Web#poor-match---possible-novel-variant)
* [FAQs](https://github.com/kelwyres/Kaptive-Web#faqs)
* [Citation](https://github.com/kelwyres/Kaptive-Web#citation)
* [Installation](https://github.com/kelwyres/Kaptive-Web#installation)
* [License](https://github.com/kelwyres/Kaptive-Web#license)
 

## Input assemblies

<b>Kaptive</b> takes as input one or more pre-assembled bacterial genomes. We use [Unicycler](https://github.com/rrwick/Unicycler) to generate high quality short-read or hybrid assemblies, but you can use your favourite assembly program.
Assemblies can be uploaded in FASTA or zipped FASTA format. Or you can upload multiple assemblies in a zipped directory (one file per sample).

## Results

When your job(s) are completed the results will be shown on-screen and will be available for access for up to 7 days - so make sure to note your token!
You can also download a summary results table, a summary json file and/or the individual K-locus FASTA sequences extracted from your input assemblies.

Find more details about these outputs [here](https://github.com/katholt/kaptive#output-files).

## Match confidence 
This is a categorical measure of match quality, optimised for use with the primary <i>Klebsiella</i> K-locus database:
* `Perfect` = the K-locus was found in a single piece with 100% coverage and 100% identity.
* `Very high` = the K-locus was found in a single piece with ≥99% coverage and ≥95% identity, with no missing genes and no extra genes.
* `High` = the K-locus was found in a single piece with ≥99% coverage, with ≤ 3 missing genes and no extra genes.
* `Good` = the K-locus was found in a single piece or with ≥95% coverage, with ≤ 3 missing genes and ≤ 1 extra genes.
* `Low` = the K-locus was found in a single piece or with ≥90% coverage, with ≤ 3 missing genes and ≤ 2 extra genes.
* `None` = did not qualify for any of the above.

WARNING: If you use the variant <i>Klebsiella</i> K-locus database please inspect your results carefully and decide for yourself what constitutes a confident match! 

## Example results and interpretation

#### Very close match

<p align="left"><img src="extras/Example_close_match.png" alt="Example close match" width="1000"></p>

The genome ATCC_BAA1705 is a close match to KL107 with 100% BLASTn identity at 100% coverage. The K-locus was found in a single assembly piece and was exactly the same length as the reference. 
All of the expected KL107 genes were found in the K-locus region of the assembly with high tBLASTx coverage and identity (indicated by dark purple shading). 
No unexpected genes were found in the K-locus region of the assembly and only a small number were found outside of the K-locus region of the assembly, which is as expected since some K-locus genes share similarity with genes in other regions of the genome. 

#### More distant match

<p align="left"><img src="extras/Example_more_distant_match.png" alt="Example distant match" width="1000"></p>

The genome UCICRE7 is a more distant match to KL2. It has 100% BLASTn coverage but only 98.72% identity. The K-locus region of the assembly is in a single piece but it is 3bp shorter than the reference.
Most of the expected KL2 genes were found within the K-locus region of the assembly at high tBLASTx coverage and identity (dark purple shading) but KL2_13 was missing (grey shading). 
Together the results suggest there may be a small deletion causing a frame-shift mutation within KL2_13. 

#### Broken assembly

<p align="left"><img src="extras/Example_broken_assembly.png" alt="Example broken assembly" width="1000"></p>

The genome MGH51 seems to be a reasonable match to the KL106 reference (99.11% coverage and 99.95% identity by BLASTn). However, the K-locus region of its assembly is in at least 6 pieces! 
When an assembly is broken into multiple pieces we should also treat <b>Kaptive's</b> results cautiously because we can't be sure about the true order of the pieces and we may have missed some pieces that contain novel genes (<b>Kaptive</b> can't find these because it only searches for known K-locus genes).  

#### Poor match - possible novel locus

<p align="left"><img src="extras/Example_novel_locus.png" alt="Example novel locus" width="1000"></p>

The genome ERR276923 best matches the KL30 reference (100% BLASTn coverage and 96.37% identity) but is missing one of the expected KL30 genes (<i>wcuG</i>, indicated by grey shading) and has an unexpected gene within the K-locus region of the assembly (KL104_18).
Five expected KL30 genes also have low coverage and/or identity tBLASTx matches (light purple shading). These genes are all in the capsule-specific region of the locus (the centre) and are adjacent to the missing gene. The combination of these results (clustered low quality gene matches, a missing gene and an unexpected gene) suggest that this genome may have a novel K-locus.
However, the K-locus region of the ERR276923 assembly is in multiple pieces so care should be taken when interpreting these results. In such a case we recommend further investigation e.g. exploring the K-locus region of the assembly graph to check for other assembly contigs that may be part of the K-locus - if these contigs contain completely novel genes <b>Kaptive</b> cannot find them!

#### Poor match - possible novel variant

<p align="left"><img src="extras/Example_novel_variant.png" alt="Example variant" width="1000"></p>

The genome 1753_ST258 is a partial match to KL107 with 99.98% BLASTn identity but only 85.56% coverage. The K-locus region of the assembly is in one piece from the left-most <i>galF</i> gene to the right-most <i>ugd</i> gene, homologues of both of which are found in almost all K-loci.
However, the K-locus region of the assembly is 2977bp shorter than the reference, and four genes are missing from the centre of the locus (<i>wbaP</i>, KL107_08, KL107_09 and KL107_10 shown in grey).
In fact, 1753_ST258 is a deletion variant of KL107. Running <b>Kaptive</b> with the <i>Klebsiella</i> K locus variants database shows that it is a very good match to KL107-D1 (shown below).

<p align="left"><img src="extras/Example_variant_database_run.png" alt="Example variant database run" width="1000"></p>  

## Databases available in Kaptive Web

Currently only <i>Klebsiella</i> K-locus databases are available in <b>Kaptive Web</b>. You can run the [command-line version of Kaptive](https://github.com/katholt/kaptive) with any appropriately formatted database of your own.
If you have a locus database that you would like to be added to <b>Kaptive Web</b> for use by yourself and others in the community, [please get in touch](https://github.com/kelwyres/Kaptive-Web/issues).

#### <i>Klebsiella</i> K-locus databases

The primary reference database comprises full-length (<i>galF</i> to <i>ugd</i>) annotated sequences for each distinct <i>Klebsiella</i> K-locus, where available:
* KL1 - KL77 correspond to the loci associated with each of the 77 serologically defined K-type references.
* KL101 and above are defined from DNA sequence data on the basis of gene content.
Note that insertion sequences (IS) are excluded from this database since we assume that the ancestral sequence was likely IS-free and IS transposase genes are not specific to the K-locus.
Synthetic IS-free K-locus sequences were generated for K-loci for which no naturally occurring IS-free variants have been identified to date.

The variants database comprises full-length annotated sequences for variants of the distinct loci:
* IS variants are named as KLN -1, -2 etc e.g. KL15-1 is an IS variant of KL15.
* Deletion variants are named KLN-D1, -D2 etc e.g. KL15-D1 is a deletion variant of KL15.
Note that KL156-D1 is included in the primary reference database since no full-length version of this locus has been identified to date. 

We recommend screening your data with the primary reference database first to find the best-matching K-locus type. If you have poor matches or are particularly interested in detecting variant loci you should try the variant database.
WARNING: If you use the variants database please inspect your results carefully and decide for yourself what constitutes a confident match! Kaptive is not optimised for accurate variant detection. 

## FAQs

#### Why are there K-locus genes found outside the K-locus?

A number of the K-locus genes are orthologous to genes outside of the K-locus region of the genome. E.g the <i>Klebsiella</i> K-locus <i>man</i> and <i>rml</i> genes have orthologues in the LPS (lipopolysacharide) locus; so it is not unusual to find a small number of genes "outside" the locus.
However, if you have a large number of genes (>5) outside the locus it may mean that there is a problem with the locus match, or that your assembly is very fragmented or contaminated (contains more than one sample).

#### How can my sample be missing K-locus genes when it has a full-length, high identity K-locus match?

<b>Kaptive</b> uses 'tblastn' to screen for the presence of each K-locus gene with a coverage threshold of 90%. A single non-sense mutation or small indel in the centre of a gene will interrupt the 'tblastn' match and cause it to fall below the 90% threshold. However, such a small change has only a minor effect on the nucleotide 'blast' match across the full locus.

#### Why does the K-locus region of my sample contain a <i>ugd</i> gene matching another locus?

A small number of the original K-locus references are truncated, containing only a partial <i>ugd</i> sequence. The reference annotations for these loci do not include <i>ugd</i>, so are not identified by the 'tblastn' search. Instead <b>Kaptive</b> reports the closest match to the partial sequence (if it exceeds the 90% coverage threshold). 

## Citation

If you use <b>Kaptive Web</b> in your research, please cite this paper:
[Wyres, K. et al. Identification of Klebsiella capsule synthesis loci from whole genome data. (2016) MGen 2, doi: 10.1099/mgen.0.000102](http://mgen.microbiologyresearch.org/content/journal/mgen/10.1099/mgen.0.000102)

## Installation
If you would like to install and run your own version of <b>Kaptive Web</b>, follow the instructions [here](./INSTALL.md).

## License

GNU General Public License, version 3

http://dx.doi.org/10.5281/zenodo.55773


