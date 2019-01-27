Releasing a new version of xbpch
================================

So you've jut incorporated a new patch or feature into **xbpch** - congratulations!
This short guide is intended to help you cut a new release of the package incorporating this new work.
By the end of this process, all **xbpch** users should be able to easily upgrade their version of the code via *pip* or *conda*.

1. Upgrade your local repository to reflect the head on "master"

$ git pull upstream master

2. Ensure that "doc/index.rst" has an entry under "Recent Changes" reflecting any new work you're including in this release

3. Open "setup.py" and increment the version number - in most cases, you'll probably increment the **MICRO** version, but for significant changes you'll probably want to reset **MICRO** to 0 and increment the **MINOR**; see `Semantic Versioning <https://semver.org/>`_ for more information

4. Commit the documentation and version changes with a commit message indicating that this is a version release

$ git commit -a -m "Release v0.X.Y"

5. Tag the release

$ git tag -a v0.X.Y -m 'v0.X.Y'

6. Push the changes and version tag upstream to master

$ git push upstream master
$ git push upstream --tags

7. Via the project GitHub page, click the "releases" button and then "Draft a new release". Select v0.X.Y and create the release; you can add documentation notes if you would like, but historically we've maintained these via the official documentation.

At this point, the automatic machinery from conda-forge and ReadTheDocs should just "work" and update the package appropriately at those places. 
You should keep an eye on the `conda-forge feedstock <https://github.com/conda-forge/xbpch-feedstock/>`_ to ensure that it builds a new release within a few hours. 
However, you'll manually need to cut a new release for PyPi.
To do this:

1. Navigate to your repository directory and issue a command to build a wheel:

$ python setup.py bdist_wheel sdist

This should create the files "dist/xbpch-0.X.Y.tar.gz" and "dist/xbpch-0.X.Y-py3-none-any.whl"

2. Upload your new wheel via twine

$ twine upload dist/xbpch-0.X.Y*

