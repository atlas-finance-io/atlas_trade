# Requests

The TWS is designed to accept up to fifty messages per second coming from the client side. Anything coming from the client application to the TWS counts as a message (i.e. requesting data, placing orders, requesting your portfolio... etc.). This limitation is applied to all connected clients in the sense were all connected client applications to the same instance of TWS combined cannot exceed this number. On the other hand, there are no limits on the amount of messages the TWS can send to the client application.
