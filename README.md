<p align="center"><img src="extras/kaptive_logo.png" alt="Kaptive" width="400"></p>

**Kaptive** reports information about surface polysaccharide loci for _Klebsiella pneumoniae_ species complex and 
_Acinetobacter baumannii_ genome assemblies. For large-scale analyses, we recommend using Kaptive on
the command line, which can be installed via [conda](), [pip]() or from [source](https://github.com/klebgenomics/Kaptive).

**Kaptive Web** is hosted online at [kaptive-web.erc.monash.edu](https://kaptive-web.erc.monash.edu) - go there to use 
the web interface, this repository hosts the code used to run the site.

**For information on how to install, run, interpret and cite Kaptive please visit the [Docs](https://kaptive.readthedocs.io/en/latest/).**

A step-by-step tutorial is also available [here](https://bit.ly/kaptive-workshop).

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.7149498.svg)](https://doi.org/10.5281/zenodo.7149498)

---
## Installing a Kaptive Web Instance
Would you like to install your own local instance of Kaptive Web? Here's how to do it!

#### Requirements

* Python >=3.8 with the following modules installed: Kaptive, pygal, pillow, reportlab, lxml. 
* These can all be installed with `pip` or `conda`:

```shell
conda create -y bioconda::kaptive conda-forge::pygal conda-forge::cairosvg conda-forge::pillow conda-forge::reportlab conda-forge::lxml \
-n kaptive_web && conda activate $_
```

#### 1. Get web2py

You'll need a local copy of [web2py](http://www.web2py.com/). Don't download the web2py app bundle, as that comes with its own copy of 
Python. We'll instead clone it from GitHub so, we can run it with our copy of Python with the necessary modules installed:

```shell
git clone --recursive https://github.com/web2py/web2py.git
```

#### 2. Get Kaptive Web

We'll put Kaptive Web into web2py's applications directory (and name it 'kaptive_web' because web2py doesn't like dashes 
in titles) and move to this directory:

```shell
git clone https://github.com/klebgenomics/Kaptive-Web web2py/applications/kaptive_web && cd $_
```

#### 3. Get Kaptive databases
Kaptive comes with `reference_databases`, however, currently Kaptive-Web needs to parse the reference Genbank to
generate the locus images. This isn't ideal, but we can save space by sym-linking `Kaptive/reference_databases` to
`web2py/applications/kaptive_web/reference_database` like so:

```shell
ln -s /path/to/kaptive/install/reference_database /web2py/applications/kaptive_web/
```

#### 4. Set paths

You now must edit the paths in the `settings.ini` file (should be in the `web2py/applications/kaptive_web` directory). 
Replace `/opt/web2py/applications/kaptive_web` with full paths (starting with '/') appropriate for your computer.

The `settings.ini` file should look something like this, but with `/opt` (the path on my computer) replaced with the path for your web2py:

```ini
[Path]
base_path = /opt/web2py/applications/kaptive_web/
reference_database_path = /opt/web2py/applications/kaptive_web/reference_database/
upload_path = /opt/web2py/applications/kaptive_web/uploads/
download_path = /opt/web2py/applications/kaptive_web/downloads/
queue_path = /opt/web2py/applications/kaptive_web/queue/

[General]
job_waiting_time = 60
refresh_waiting_time = 60000
```

#### 5. Launch web2py

```shell
cd ..  # go back to the web2py directory
python web2py.py
```

A window should pop up asking for a password (you don't need to change anything else). 
Give it one, and you'll be able to view the web2py interface at [http://127.0.0.1:8000](http://127.0.0.1:8000).

#### 6. Use Kaptive Web

You'll now be able to use Kaptive Web at 
[http://127.0.0.1:8000/kaptive_web/default/index](http://127.0.0.1:8000/kaptive_web/default/index). 
You can also get there by going to 'My Sites' in the web2py interface, entering your password, and clicking on 
'kaptive_web'.

Enjoy!

## Disabling reCAPTCHA

If you are running a local copy of Kaptive Web, you may want to get rid of the 
[reCAPTCHA](https://www.google.com/recaptcha/) "I'm not a robot" check.

You can do this by making a couple small modifications to the `controllers/default.py` file. Specifically, delete the 
two instances of `captcha_field()`. Kaptive Web will now assume you're not a robot!


