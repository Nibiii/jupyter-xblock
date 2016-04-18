/* Javascript for JupyterhubXBlock. */
function JupyterhubXBlock(runtime, element) {

  /* TODO support for other browsers */
  chrome.webRequest.onBeforeSendHeaders.addListener(
    function(details){
      var headers = details.requestHeaders;
      debugger;
      return { requestHeaders : headers };
    },
    { urls: [ "*://*/user/*/notebooks/*" ] },
    [ 'blocking', 'requestHeaders' ]
  );

}
