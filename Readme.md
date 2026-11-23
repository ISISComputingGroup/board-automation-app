# Automation for ISIS Experiment Controls GitHub projects

# Purpose
There are a number of things related to project management of projects within GitHub which can be automated.

This repository contains those specifically used by the Experiment Controls Group at ISIS Pulsed Neutron and Muon Source.

# To use
This can be run as a test application on a developer work station if you use app.py

To use this alongside our JSONBourne server copying of these directories and replacing webserver_forJSONBourne in the appropriate directory with webserver_forJSONBourne_and_git_automation should allow both to be used alongside each other. JSONBourne is no longer in use for anything critical, and will be removed in the future.
Note that you will also need to generate a python install potentially depending on the server.

Configuration information is detailed in the [Configuration Readme](/config_info/config_readme.md).

The labels, statuses and other required setups are detailed in the [Required Items](doc/required_items.md) page.

# Graph QL Naming Convention Used
Within graph_ql_queries simple queries are in camel case (camelCase) whilst mutations, which make changes to the projects, repositories, or issues are in Pascal case (PascalCase).
This convention is simply to make it clearer at a glance whether the ql query in use should be making changes or not.

