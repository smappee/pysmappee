Official Smappee Python Library
===============================

Python Library for the Smappee dev API (v3) and MQTT interface. Used as a wrapper dependency in the [Home Assistant integration](https://www.home-assistant.io/integrations/smappee).

Version
-------

0.2.23

Installation
------------
The recommended way to install is via [pip](https://pypi.org/)

    $ pip3 install pysmappee

Changelog
---------
0.0.1
* Initial commit

0.0.2
* Rename smappee directory

0.0.3
* Sync dev API

0.0.{4, 5, 6}
* Actuator connection state
* Platform option
* Measurement index check
* Location details source change

0.0.{7, 8, 9}
* Support comfort plug state change
* Add locations without active device
* Disable IO modules
* Align connection state values

0.1.{0, 1}
* Refactor api to work with implicit account linking
* Only keep farm variable in API class

0.1.{2, 3}
* Only use local MQTT for 20- and 50-series
* 11-series do have solar production

0.1.4
* Extend service location class with voltage and reactive bools
* Extend model mapping

0.1.5
* Catch expired token as an HTTPError

0.2.{0, .., 9}
* Implement standalone local API
* Only create objects if the serialnumber is known
* Review local API exception handling

0.2.10
* Phase 2 Local API (support Smappee Pro/Plus)
* Local API improvements (Switch current status, cache load)

0.2.11
* Activate IO modules

0.2.{12, 13}
* Move requirements to setup.py file

0.2.14
* Exclude test package

0.2.{15, 16, 17}
* Review consumption and production indices for solar series
* Fix caching for local polling

0.2.{18, ..., 23}
* Prepare local Smappee Genius support (local mqtt)
* Remove smart device support

Support
-------
If you find a bug, have any questions about how to use PySmappee or have suggestions for improvements then feel free to 
file an issue on the GitHub project page [https://github.com/smappee/pysmappee](https://github.com/smappee/pysmappee).

License
-------
(MIT License)

