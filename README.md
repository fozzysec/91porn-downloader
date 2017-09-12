***Auto Downloader***

This is a video downloader for 91porn888.com

**pre-requisites**

```
sudo pip3 install gevent
sudo pip3 install lxml
sudo pip3 install requests
```

create directory `videos`

**usage**

91porn.py &lt;username&gt; &lt;password&gt; &lt;save-list-file-name&gt; &lt;start-page-number&gt; &lt;end-page-number&gt;

example:`./91porn.py foo bar my-list.txt 1 50`

**proxy settings**

To use `HTTP` proxy, you need to set the environment variable by

```
export HTTP_PROXY="http://server:port"
```

To use `SOCKS5` first you need to install `requests` with `socks` support by the following command

```
sudo pip3 install requests[socks]
```

Then set up proxy by

*local dns resolve*

```
export HTTP_PROXY="socks5://server:port"
```

*remote dns reslove*

```
export HTTP_PROXY="socks5h://server:port"
```

**notice**

the script will log downloaded videos and will skip them.

currently the website uses javascript to deduct credits and can be passthrough by this script, no credits are needed to download videos.

~~The website has updated the function of deducting credits to perform at the server-end, so to download large amount of videos you may need a VIP account.~~

To make downloader become multi-threading, remove gevent imports and remove `monkey.patch_all()`
