## OLG Proline

- Live odds updates are sent through a json payload with the url of the form:
	https://us1.offering-api.kambicdn.com/offering/v2018/olgsportscaon/listView/tennis/all/all/all/in-play.json?channel_id=1&client_id=200&lang=en_CA&market=CA-ON&useCombined=true&useCombinedLive=true

    https://offering.sbo.fra-hub.workload.shapegamescloud.com/olgsportscaon/api/compact_events?event=1027873537&event=1027873539&event=1027873777&event=1027873771&event=1027873773&event=1027873770&event=1027873776&event=1027873769&event=1027873772&event=1027873775&include_default_markets=true&lang=en-CA&market=CA-ON

- These are not delta patches, but large json objects displaying information on the entire opened page similar to Fanduel's schema.

- Proline does not have a reference dictionary like other sportboooks. As soon as "in-play.json" response is received, the page loads
completely with all information needed.