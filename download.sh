#!/bin/sh

download_index () {
	i=1
	while [ $i -le 10 ] ;
	do
		curl -K ghdwn.curl --data-urlencode "page=$i" | \
			tee json/$i.json | \
			jq '.items | .[] | .clone_url' > urls/$i

		i=$((i+1))
	done;

	cat urls/* > repos/index.txt
}


cd repos
for url in `cat index.txt`
do
	git clone $url
done
