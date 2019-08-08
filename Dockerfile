FROM cs50/server
EXPOSE 8080

# dependencies
RUN apt-get update && apt-get install -y libmysqlclient-dev
RUN pip3 install --upgrade -r requirements.txt
CMD bash -c 'HELPERS_PATH=$(python docker-cmd.py) && export HELPERS_PATH && passenger start'
