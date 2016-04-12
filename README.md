# edx_xblock_jupyter

XBlock intended to display and manage Jupyter Notebooks.
The Xblock requires that JupyterHub be installed, and the following configuration options set:

In the JupyterHub configuration file passed as a command line argument:
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
#### Admin Acess
Admin(s) must be defined and admin user credentials must be supplied to the Xblock so that it can perform administrator REST API calls to JupyterHub.

1. Admin users:
```py
c.Authenticator.admin_users = {'mal', 'zoe'}
```
2. User whitelists (optional)
```py
""" Admins automatically added """
c.Authenticator.whitelist{'Zoe', 'Chloe'}
```
3. Default edx user is available as (this is created on deployment of JupyterHub):
```py
""" (TODO: Update this scheme) password: edx """
c.Authenticator.admin_users = set('edx_xblock_jupyter')
```
4. This must be set in the config for API to not result in a 403
```py
c.JupyterHub.admin_access = True
```
#### Load Iframes in the same window

```py
Fill in settings
```

## REST API calls to JupyterHub
The Xblock creates a user by calling the JupyterHub REST API whenever a user attempts to access a Jupyter Notebook. The created user on JupyterHub will share the unique username used on the edx-platform. In this scenario each user will have their own Notebook.

## Behaviour
```TODO``` Loading a Jupyter Notebook through the Xblock options, will set that Notebook for that course unit.
