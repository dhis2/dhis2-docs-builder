pip3 install -r requirements.txt

cd tools/python/markdown-pp-master
pip3 install -e .
cd -

cd tools/python/markdown-extensions/d_card
pip3 install -e .
cd -

cd tools/python/dhis2_plugins
pip3 install -e .
cd -
