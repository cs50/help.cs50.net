FROM cs50/server:focal
EXPOSE 8080

# dependencies
RUN apt-get update && apt-get install -y libmysqlclient-dev
RUN pip3 install --upgrade -r requirements.txt
CMD bash -c 'HELPERS_PATH=$(python3 docker-cmd.py) && export HELPERS_PATH && passenger start'
