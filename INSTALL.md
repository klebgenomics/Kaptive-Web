## Installation
* Download Web2Py framework from [here](http://www.web2py.com/). Installation guide can be found [here](http://web2py.com/books/default/chapter/29/13/deployment-recipes).
* The default work directories ````/opt/kaptvie```` structure. These settings may be modified in ````settings.ini```` file.

````
.
├── kaptive.py
├── queue
│   └── queue
├── reference_database
│   ├── 1-Klebsiella_k_locus_primary_reference.gbk
│   ├── 2-Klebsiella_k_locus_variant_reference.gbk
│   └── wzi_wzc_db.fasta
└── uploads
````  

* Install the dependencies for <b>Kaptive</b> command-line version. The installation guide can be found [here](https://github.com/katholt/Kaptive#installation).
* Download <b>Kaptive</b> command-line version from [here](https://github.com/katholt/kaptive), and copy the files to relevant directory. 
* Install ````pygal````, ````pillow```` with ````pip````.
* Install ````imagemagick````, installation guide can be found [here](https://www.imagemagick.org/script/binary-releases.php).