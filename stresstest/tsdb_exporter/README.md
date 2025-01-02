# TSDB Exporter ( InfluxDB for now )
An simple metric exporter for prometheus. More details soon.

## Usage example
> Simple usage, only one query with a label
```shell
$ curl -s -k -o /dev/null -X GET -H "Authorization: Bearer f575e88935ac5bfeaf7047d1d90da343a20fb16822abe5d0188369b91e09efdf" --write-out '%{json}' https://localhost:4433/quizzes/ | exporter.py --label curl-http
```

> With this, you can control the number of process to start ( Like VUsers)
```shell
$ while true; do seq 20 | xargs -P20 -I{} sh -c 'curl --http3 -s -k -o /dev/null -X GET -H "Authorization: Bearer f575e88935ac5bfeaf7047d1d90da343a20fb16822abe5d0188369b91e09efdf" --write-out "%{json}" https://localhost:4433/quizzes/ | ./exporter.py --label curl-quic' ; done
```