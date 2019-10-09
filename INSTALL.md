<p align="center"><img src="extras/kaptive_logo.png" alt="Kaptive" width="400"></p>

## Installing Kaptive Web

Would you like to install your own local instance of Kaptive Web? Here's how to do it!


#### Requirements

* Python 2.7 with the following modules installed: pygal, pillow, BioPython, reportlab, lxml:
  * `pip install pygal pillow BioPython reportlab lxml` (You might need `sudo`, if you're installing for your system's copy of Python.)
* [BLAST+](http://www.ncbi.nlm.nih.gov/books/NBK279690/) command line tools (specifically `makeblastdb`, `blastn` and `tblastn`) available in your PATH.
* The ImageMagick command line tool `convert`, with svg support.
  * If installing on a Mac with homebrew, use `brew install imagemagick --with-librsvg`



#### 1. Get web2py

You'll need a local copy of [web2py](http://www.web2py.com/). Don't download the web2py app bundle, as that comes with its own copy of Python. We'll instead clone it from GitHub so we can run it with our copy of Python with the necessary modules installed.

```
git clone --recursive https://github.com/web2py/web2py.git
```



#### 2. Get Kaptive Web

We'll put Kaptive Web into web2py's applications directory (and name it 'kaptive' because web2py doesn't like dashes in titles). It also needs a queue directory, so we'll make that now.

```
cd web2py/applications
git clone https://github.com/kelwyres/Kaptive-Web kaptive
mkdir kaptive/queue
```



#### 3. Get command line Kaptive

Also download the [command line version of Kaptive](https://github.com/katholt/Kaptive) and put the files we need into our Kaptive Web directory.

```
git clone https://github.com/katholt/Kaptive kaptive-CLI
cp kaptive-CLI/kaptive.py kaptive/
cp -r kaptive-CLI/reference_database kaptive/
```



#### 4. Set paths

You now must edit the paths in the `settings.ini` file (should be in the `web2py/applications/kaptive` directory). Replace `/opt/web2py/applications/kaptive` with full paths (starting with '/') appropriate for your computer.

The `settings.ini` file should look something like this, but with `/Users/Ryan/Desktop` (the path on my computer) replaced with the path for your web2py:

```
[Path]
base_path = /Users/Ryan/Desktop/web2py/applications/kaptive/
reference_database_path = /Users/Ryan/Desktop/web2py/applications/kaptive/reference_database/
upload_path = /Users/Ryan/Desktop/web2py/applications/kaptive/uploads/
download_path = /Users/Ryan/Desktop/web2py/applications/kaptive/downloads/
queue_path = /Users/Ryan/Desktop/web2py/applications/kaptive/queue/

[General]
job_waiting_time = 60
refresh_waiting_time = 60000
```




#### 5. Launch web2py

Launching web2py is pretty easy!

```
cd ..  # go back to the web2py directory
python web2py.py
```

A window should pop up asking for a password (you don't need to change anything else). Give it one and you'll be able to view the web2py interface at [http://127.0.0.1:8000](http://127.0.0.1:8000).




#### 6. Use Kaptive Web

You'll now be able to use Kaptive Web at [http://127.0.0.1:8000/kaptive/default/index](http://127.0.0.1:8000/kaptive/default/index). You can also get there by going to 'My Sites' in the web2py interface, entering your password, and clicking on 'kaptive'.

Enjoy!





## Disabling reCAPTCHA

If you are running a local copy of Kaptive Web, you may want to get rid of the [reCAPTCHA](https://www.google.com/recaptcha/) "I'm not a robot" check.

You can do this by making a couple small modifications to the `controllers/default.py` file. Specifically, delete the two instances of `captcha_field()`. Kaptive Web will now assume you're not a robot!
