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

    - Click on the course you wish to add the Xblock to.
    - At the top of the page click on the settings drop down and select Advanced settings.
    - Under 'Manual Policy Definition' find 'Advanced Module List'
    - Add the name of the xblock to the list. This is the package name of the xblock found in setup.py in the root of the xblock's directory,
    setup.py:
    ```py
    packages=['edx_xblock_jupyter']
    ```
    - Save changes.

#### Note

Studio needs to be running in order for Instructors to use the Xblock, and upload notebooks. In the lms, the Xblock will pull the base notebook and create it remotely in the docker container's volume if it doesn't exist, using sifu api calls. If Studio is not running, and the base notebook does not exist in the docker container's volume, then students will see an empty notebook.

## Oauth2 Flow and Behaviour:

1. App requests an authorization grant for a client_id from the lms. Since the user is logged in, and authorization grant is returned.
2. The Xblock requests an access token from Sifu, the authorization grant is sent along with.
3. Sifu checks the authorization grant is valid for the user, and then creates a token for access to its services. The token is returned to the Xblock.
4. In all other calls to Sifu, this token is presented in the header data so that the call is authenticated. The only exception is when the Xblock is requesting a notebook. In this scenario the token is placed in the query string, because the query string is the notebook iframe's url. This is actually not ideal (or safe!), and we are actively looking at alternate means of providing the token in the header for iframe calls.
5. Once the Xblock is authenticated for a user it:
    - Checks if the course unit's base notebook exists remotely. If not, it uploads it.
    - If the base file does exist, it checks if the user's notebook exists. If not it creates it.
    - If the user's notebook exists, it renders the notebook in the iframe.
6. Sifu checks that a User is authenticated, also that the requested notebook matches their username. This means that an authenticated user can't request someone else's notebook. Sifu also is the only service allowed to make a call to the jupyter api to load a notebook. In addition, the notebook cannot be loaded anywhere else except where the frame ancestor matches your lms domain.
