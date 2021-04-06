![Release](https://img.shields.io/github/v/release/cmason3/jinjafx)
![Size](https://img.shields.io/github/languages/code-size/cmason3/jinjafx?label=size)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[<img src="https://img.shields.io/badge/Web%20Front--End-https%3A%2F%2Fjinjafx.io-orange" align="right">](https://jinjafx.io)

<h1 align="center">JinjaFx Server - Jinja2 Templating Tool</h1>
<h3 align="center">:star: Harness the Power of Jinja2 Templates with Dynamic CSV or YAML as Input :star:</h3>

JinjaFx Server is a lightweight web server that provides a web frontend to JinjaFx. It is a separate Python file which imports JinjaFx to generate outputs from a web interface - it does require the "requests" module which isn't in the base install. Usage instructions are provided below, although it is considered an additional component and not part of the base JinjaFx tool, although it is probably a much easier way to use it.

### JinjaFx Server Usage

Once JinjaFx Server has been started with the `-s` argument then point your web browser at http://localhost:8080 and you will be presented with a web page that allows you to specify `data.csv`, `template.j2` and `vars.yml` and then generate outputs. If you click on "Export" then it will present you with an output that can be pasted back into any pane of JinjaFx to restore the values.

```
 jinjafx_server.py -s [-l <address>] [-p <port>] [-r <repository> | -s3 <aws s3 url>] [-rl <rate/limit>] [-api]
   -s                          - start the JinjaFx Server
   -l <address>                - specify a listen address (default is '127.0.0.1')
   -p <port>                   - specify a listen port (default is 8080)
   -r <repository>             - specify a local repository directory (allows 'Get Link')
   -s3 <aws s3 url>            - specify a repository using aws s3 buckets (allows 'Get Link')
   -rl <rate/limit>            - specify a rate limit (i.e. '5/30s' for 5 requests in 30 seconds)
   -api                        - start in api only mode without web frontend

 Environment Variables:
   AWS_ACCESS_KEY              - specify an aws access key to authenticate for '-s3'
   AWS_SECRET_KEY              - specify an aws secret key to authenticate for '-s3'
```

For health checking purposes, if you specify the URL `/ping` then you should get an "OK" response if the JinaFx Server is up and working (these requests are omitted from the logs). The preferred method of running the JinjaFx Server is with HAProxy in front of it as it supports TLS termination and HTTP/2 - please see the `docker` directory for more information.

The "-r" or "-s3" arguments (mutually exclusive) allow you to specify a repository ("-r" is a local directory and "-s3" is an AWS S3 URL) that will be used to store DataTemplates on the server via the "Get Link" and "Update Link" buttons. The generated link is guaranteed to be unique and a different link will be created every time - version 1.3.0 changed the behaviour, where previously the same link was always generated for the same DataTemplate, but this made it difficult to update DataTemplates without the link changing as it was basically a cryptographic hash of your DataTemplate. If you use an AWS S3 bucket then you will also need to provide some credentials via the two environment variables which has read and write permissions to the S3 URL.

The "-rl" argument is used to provide an optional rate limit of the source IP - the "rate" is how many requests are permitted and the "limit" is the interval in which those requests are permitted - it can be specified in "s", "m" or "h" (e.g. "5/30s", "10/1m" or "30/1h").

The "-api" argument is used to disable the web frontend and only provide the api which the frontend uses - the api is currently undocumented so this option isn't recommended in normal use cases.

### Shortcut Keys

As well as supporting the standard CodeMirror shortcut keys for the "data.csv", "vars.yml" and "template.j2" panes, it also supports the following custom shortcut keys:

- F11 / Cmd-Enter - Toggle Fullscreen

- Ctrl-G / Cmd-G - Generate

- Ctrl-S / Cmd-S - Update Link

- Ctrl-F / Cmd-F - Find

### Data Sets

The Data Set feature allows you to include multiple different "data.csv" and "vars.yml" contents while maintaining the same "template.j2". This is to support scenarios where you have different Data Sets for your Live vs your Test environments, but the template should be the same. There are no limits on the number of different Data Sets that can be added to a single DataTemplate (the name must start with a letter and only contain alphanumerical, "-", " " or "_" characters). When you click "Generate" it will use the currently active Data Set to generate the output - clicking on the name of the current Data Set (by default there is a single "Default" Data Set) allows you to switch between the different Data Sets.

### JinjaFx Input

This advanced feature allows you to specify an input form that can be used to obtain inputs for your Jinja2 template when you click on "Generate". As JinjaFx is built on Bootstrap 4, it uses the <a href="https://getbootstrap.com/docs/4.6/components/modal/#modal-components">Bootstrap 4 Modal</a> syntax to specify what is contained in the body of your modal form. You define an input form using the `jinjafx_input` variable within your "vars.yml" file as per the following simple example:

```yaml
---
jinjafx_input:
  body: |2
    <div class="row">
      <div class="col-6">
        <label for="name" class="col-form-label">Name</label>
        <input id="name" class="form-control" data-var="name" required>
      </div>
      <div class="col-6">
        <label for="gender" class="col-form-label">Gender</label>
        <select id="gender" class="form-control" data-var="gender">
          <option value="male">Male</option>
          <option value="female">Female</option>
        </select>
      </div>
    </div>
```

You can also specify an optional `size` attribute alongside the `body` attribute which sets the width of the modal using the pre-defined Bootstrap 4 sizes (i.e. "sm", "lg" and "xl"). The input form supports full native HTML validation using `required` and `pattern` attributes. The values which are input are then mapped to Jinja2 variables using the `data-var` custom attribute (e.g. `data-var="name"` would map to `jinjafx_input['name']`):

```jinja2
Name: {{ jinjafx_input['name'] }}
Gender: {{ jinjafx_input['gender'] }}
```

If you specify the same `data-var` value more than once in the input form then the variable will be converted into a list using the values in the order they appear in the form.
