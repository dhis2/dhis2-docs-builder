window.onload = (event) => {

const redirect_map = {
  '#webapi_tei_grid_query_request_syntax': 'develop/using-the-api/dhis-core-version-master/tracker.html#webapi_tracked_entity_instance_management',
  '#sms-command-values': 'develop/using-the-api/dhis-core-version-master/sms.html#webapi_sms_commands',
  '#dataAdmin_scheduling_config': 'use/user-guides/dhis-core-version-master/maintaining-the-system/scheduling.html',
  '#testing': '~/en/develop/dhis2-developer-guide/dhis-core-version-235/apps.html#apps_purpose_packaged_apps',
}

  if (window.location.hash in redirect_map) {
  window.location = redirect_map[window.location.hash]
}
};
