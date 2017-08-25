#!/usr/bin/python


from python_ltspice_tools import *

##Read netlist file into the netlist object
original_filename = "C:/_data_cv/ERS/CV/System sizing/simulation/CA_sur_feeders.net"
original_netlist = netlist_class(original_filename)
raw_values = original_netlist.run_netlist()
for node, node_value in raw_values.node_values.items():
    test = .5 #s
    result = raw_values.find_node_value_at_independet_value(given_independent_value=test,given_node=node_value)
    print(node,result)