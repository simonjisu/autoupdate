# AutoUpdate

 - version: 0.1


## Docker 

This docker is based on `Ubuntu 18.04` and installed `python3.6` + `seleuim` + `superset`

After installed docker, pull this image like below

```
$ docker pull simonjisu/autoupdate
```

and run the docker. port `8088` is for superset basic port you can ignore it.

```
$ docker run -i -t -p 8088:8088 --name [name] -v [data-volume] simonjisu/autoupdate
```

there is another version for arm32v7/debian, pull the docker using tag "arm-debian"

```
$ docker pull simonjisu/autoupdate:debian
```

## installation

This installation is for Internal use, however you can modify codes in `src` directory for your own purpose.

```
wget https://gist.githubusercontent.com/simonjisu/3cf5d858746b11228ff24a09dbf4c832/raw/385a5b33f8617ec553dc8f9aaf0f6bd52a924135/autoupdate_installer.sh
```

insert arguments behind `autoupdate_installer.sh`, 1\~2 is upto site login information, 3\~7 is related to superset admin.

1. login-email
2. login-password
3. username  
4. firstname
5. lastname
6. email
7. password
