# install dependencies
# pip3 install -r requirements.txt
PIP_CONSTRAINT=constraints.txt pip3 install -r requirements.txt --no-cache

# install custom plugins
pip3 install -e tools/python/markdown-pp-master
pip3 install -e tools/python/markdown-extensions/d_card
pip3 install -e tools/python/dhis2_plugins
