curl -X GET http://admin:admin@172.26.134.187:5984/twitter/_all_docs?include_docs=true > ./db.json

curl -d @db.json -H "Content-Type: application/json" -X POST http://admin:admin@172.26.134.146:5984/twitter/_bulk_docs

curl -X PUT http://admin:admin@172.26.134.146:5984/twitter/_design/Data -d @db-views.json





curl -d @pollutant.json -H "Content-Type: application/json" -X POST http://admin:admin@172.26.134.146:5984/pollutant/_bulk_docs

curl -X PUT http://admin:admin@172.26.134.146:5984/pollutant/_design/Pollution -d @pollutant-views.json