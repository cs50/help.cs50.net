FROM cs50/server
EXPOSE 8080

# for development
ENV PATH /srv/www/opt/cs50/help50/bin:"$PATH"

# dependencies
RUN apt-get update && apt-get install -y libmysqlclient-dev
RUN pip3 install --upgrade -r requirements.txt
CMD bash -c 'HELPERS_PATH=$(python3 -c "import os, lib50; lib50.set_local_path(os.getenv(\"HELP50_PATH\")); print(lib50.local(os.getenv(\"HELPERS_SLUG\")))") passenger start'
