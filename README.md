# Radio to get bbc shows in a Docker image

```
docker build --tag python-docker .
docker run -t  -p 80:5000 -v "c:\tmp":/output --name alldock --mount source=radio_data,target=/radio_data alldock
gcloud run deploy --port=5000
docker run -t  -p 80:5000 -v "c:\tmp":/output alldock
docker run -t  -p 80:5000  alldock
```

docker push colin999/alldock

docker run -d  -p 80:5000 colin999/alldock


## commands
apt-get update
apt-get install software-properties-common
add-apt-repository ppa:m-grant-prg/utils
apt-get update
apt install get-iplayer


apt install get-iplayer -y



apk update
apk add ruby
get_iplayer --force --output "/tmp/"    --file-prefix="<firstbcastdate>~<nameshort>~<episode>~<pid>" --type=radio --radio-quality="std,med" --pid=m001614b




# get_iplayer PVR Docker image

This is a smallish (100MB) Docker image that hosts the [get_iplayer](https://github.com/get-iplayer/get_iplayer/wiki) PVR. It automatically keeps itself up-to-date with the latest version of get_iplayer.

The PVR recording feature runs hourly. The get_iplayer version is updated daily.

## Image configuration

The PVR can be accessed by default on port `1935/tcp`. Set the environment variable `PORT` to override.

Downloaded TV & radio files will be placed in the `/output` bind mount.

Environment variables `PUID` and `PGID` can be set to dictate the owner and group of downloaded files (useful if you're putting these files in a shared folder).

If you're running behind a reverse proxy set the environment variable `BASEURL` to the full proxy URL.

## Example invocation

This makes the PVR available on port 1935, and makes downloaded files owned by the current user:

```sh
docker run -d -e PUID=`id -u` -e PGID=`id -g` -p 1935:1935 -v /destination/on/host:/output marginal/get_iplayer:latest
```
Replace `/destination/on/host` with the path of a folder on the host machine where you would like the downloaded files to be placed.

## get_iplayer configuration

get_iplayer's configuration and cache will be written to the `.get_iplayer` subfolder under the `/output` bind mount. You can set get_iplayer [options](https://github.com/get-iplayer/get_iplayer/wiki/options) in the file `/destination/on/host/.get_iplayer/options`.

Refer to the file [options.sample](https://raw.githubusercontent.com/Marginal/docker-get_iplayer/master/options.sample) for examples.

## Migrating an existing get_iplayer installation

1. Copy your existing `.get_iplayer` folder over to `/destination/on/host/.get_iplayer` .

2. If you have a `.get_iplayer/options` file, open it in a text editor and remove any `output`, `outputradio` and/or `outputtv` statements.

3. Open the file `.get_iplayer/download_history` in a text editor, search for "/old/destination/folder/" and globally replace with "`/output/`".
