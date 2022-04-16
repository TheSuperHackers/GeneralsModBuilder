set venvDir=.venv
set venvExe=%venvDir%\Scripts\python
set pyExe=python

%pyExe% -m venv %venvDir%
%venvExe% -m pip install wheel
%venvExe% -m pip install -r requirements-dev.txt
%venvExe% setup.py sdist bdist_wheel --dist-dir=.dist
