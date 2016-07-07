# edx-xblock-jupyter

XBlock intended to display and manage Jupyter Notebooks.
The Xblock requires the following:

#### What You Need To Do

1. Make sure that Lms and Studio are set up correctly for the Xblock:
    - Oauth2
        * Make feature setting 'ENABLE_OAUTH2_PROVIDER' set to true. This allows Edx to be an Oauth2 provider
          for the service we are connecting to.
        * Go into the Admin backend and set up a client, and make that client Trusted.
          This assumes you will have decided on a domain name for the Sifu service, or EB DNS name.
          You can edit this later however should the URL change. You can generate or chose your own
          client ID and secret.
          ```text
          url:           http://sifu_example.com
          redirect uri:  http://edx_lms_domain.com
          client id:     some_id
          client secret: somesecret
          ```
    - Django Middleware: crequest
        * Make sure ```crequest``` is installed: ```sudo -H -u edxapp /edx/bin/pip.edxapp install django-crequest```
          Or add to ansible deployment.
        * In order to handle Oauth2 grant flows, the xblock needs access to session ID's, and other Cookie data.
          Update  INSTALLED_APPS and MIDDLEWARE_CLASSES as follows:
          ```.py
           INSTALLED_APPS += ('crequest')

           MIDDLEWARE_CLASSES += (
               ...
               'crequest.middleware.CrequestMiddleware',
           )
           ```
2. Deploy the following Docker project on AWS Elastic Beanstalk: [proversity-docker-jupyternotebook](https://github.com/proversity-org/proversity-docker-jupyternotebook)
Follow the instruction for set up in the project's README. You will need your Oauth2 client details handy.

3. Clone the repo and update the settings in config.yml:
    ```yml
    'sifu_domain': 'eb-dns-name'
    'studio_domain': 'studio-domain-name'    
    ```
    Include port number on studio if needed, sifu_domain port defaults to 3334.

4. Install the xblock: ```sudo -H -u edxapp /edx/bin/pip.edxapp install --upgrade /path/to/edx_xblock_jupyter/```.

5. Add the Xblock in Studio.

    1. Click on the course you wish to add the Xblock to.
    2. At the top of the page click on the settings drop down and select Advanced settings.
    3. Under 'Manual Policy Definition' find 'Advanced Module List'
    4. Add the name of the xblock to the list. This is the package name of the xblock found in setup.py in the root of the xblock's directory,
    setup.py:
    ```py
    packages=[
        'edx_xblock_jupyter',
    ]
    ```
    5. Save changes.

#### Note

Studio needs to be running in order for Instructors to create the xblock, and upload notebooks. In the lms, the xblock will pull the base notebook   and create it remotely in the docker container's volume if it doesn't exist, using sifu api calls. If Studio is not running, and the base notebook does not exist in the docker container's volume, then students will see an empty notebook.

#### Content Security
Update these with the intended hostnames and port numbers, of a frame ancestor.

E.g. A notebook is served in an iframe hosted www.example.com. The Content-Security-Policy would then be:

```py
""" This is for the JupyterHub CSP settings """
c.JupyterHub.tornado_settings = {
    'headers': {
        'Content-Security-Policy': " 'www.example.com:80' "
  }
}
...
""" This is for the JupyterNotebook CSP settings """
c.Spawner.args = ['--NotebookApp.tornado_settings={ \'headers\': { \'Content-Security-Policy\': "\'www.example.com:80\'"}}']
```

## Oauth2 Flow and Behaviour:

1. Use Edx as an oauth provider, and request an access token from sifu. If this is not a logged in edx user, there will be no joy.
2. Check the existence of the course unit's base notebook file.
3. Upload it if it doesn't exist.
4. Check if the user's course unit notebook exists
5. Create one from the base file if it doesn't exist
6. Request the user's notebook in an Iframe

All API requests to Sifu include the access token provider at the authorization stage.
