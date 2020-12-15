## jinjafx.yml

```
apiVersion: v1
kind: Service
metadata:
  name: jinjafx
  labels:
    app: jinjafx
spec:
  type: ClusterIP
  clusterIP: 10.152.183.100
  selector:
    app: jinjafx
  ports:
    - protocol: TCP
      port: 8080

---

apiVersion: apps/v1
kind: Deployment
metadata:
  name: jinjafx
spec:
  selector:
    matchLabels:
      app: jinjafx
  replicas: 1
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxUnavailable: 0
      maxSurge: 1
  template:
    metadata:
      labels:
        app: jinjafx
    spec:
      dnsPolicy: Default
      containers:
        - name: jinjafx
          image: docker.io/cmason3/jinjafx:latest
          args: [ "-rl", "5/30s" ]
          imagePullPolicy: Always
          ports:
            - containerPort: 8080
          readinessProbe:
            httpGet:
              port: 8080
              path: /ping
              scheme: HTTP
            initialDelaySeconds: 30
            periodSeconds: 60
            timeoutSeconds: 5
          livenessProbe:
            httpGet:
              port: 8080
              path: /ping
              scheme: HTTP
            initialDelaySeconds: 180
            periodSeconds: 30
            timeoutSeconds: 5
```
