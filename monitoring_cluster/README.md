# Monitoring Cluster

## Architecture Diagrams
![Architecture Diagram](./assets/diagrams.png)


1. Turn on Airflow webserver:
```bash
airflow webserver -p 8081
```

2. Turn on Airflow scheduler:
```bash
airflow scheduler
```

3. Write your dags in right folder
`neu_solution/dags`


## Kill old dags

1. Check pid run in 8081 and 8793 and kill it
```bash
lsof -i :8081
```

and kill them



