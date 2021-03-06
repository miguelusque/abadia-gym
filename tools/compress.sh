#!/bin/bash
echo "Updating the all  actions lists to speed it up"
echo "and avoid to destroy existing gzips (we need to fix and improve iti **Mostly fixed)"
tools/create_all_actions_lists.sh
for file in `curl https://storage.googleapis.com/abadia-data/all_abadia_actions_list.txt | grep $1 | grep -v ".gz"`
do
  echo "$file"
  gs=`echo $file | sed -e 's/https\:\/\/storage\.googleapis\.com/gs\:\//'`
  echo "$gs"
  gsutil ls -l $gs
  ret=$?
  case $ret in
    0)
        curl $file | gzip - | gsutil cp - $gs.gz && gsutil rm $gs
        gsutil ls -l $gs.gz
        ;;
    *)
        echo "Looks like there is an problem with $gs"
        ;;
  esac
done
