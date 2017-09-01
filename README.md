**Auto Downloader**

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

**notice**

the script will log downloaded videos and will skip them.
currently the website uses javascript to deduct credits and can be passthrough by this script, no credits are needed to download videos.

To make downloader become multi-threading, remove gevent imports and remove `monkey.patch_all()`
