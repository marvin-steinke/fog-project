apt-get update
apt-get install redis-tools redis-server python3-pip git -y
cd /opt
git clone --depth 1 https://github.com/marvin-steinke/fog-project.git
cp -r fog-project/cloud/gcloud_deployment server
rm -rf fog-project
cd server
pip3 install -r requirements.txt
# uncomment for automatically starting cloud-server application
python3 cloud-server.py &
cd web-client
python3 data_fetcher.py &
