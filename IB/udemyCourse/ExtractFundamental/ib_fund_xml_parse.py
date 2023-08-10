# -*- coding: utf-8 -*-
"""
IB API - Fetching Fundamental Data (stock) and parsing the xml file

@author: Mayank Rasu (http://rasuquant.com/wp/)
"""


import xml.etree.ElementTree as ET
import pandas as pd
import os

os.chdir("D:\\Udemy\\Interactive Brokers Python API\\11_fundamental_date")

f = open("ticker0_fundamental.xml","r")
xml_dump = f.read()
f.close()

name_map = {}
inc_st = {}
bal_st = {}
cs_st = {}

tree = ET.fromstring(xml_dump)
for child in tree:
    if child.tag == "FinancialStatements":
        for fs_elm in child:
            if fs_elm.tag == "COAMap":
                for coa_elm in fs_elm:
                    name_map[coa_elm.get("coaItem")]=coa_elm.text
            if fs_elm.tag == "AnnualPeriods":
                for ap_elm in fs_elm:
                    date = ap_elm.get("EndDate")
                    inc_st[date] = {}
                    bal_st[date] = {}
                    cs_st[date] = {}
                    for fiscal in ap_elm:
                        if fiscal.get("Type")=="INC":
                            for fiscal_elm in fiscal:
                                if fiscal_elm.tag == "lineItem":
                                    inc_st[date][fiscal_elm.get("coaCode")]=fiscal_elm.text
                                    
                        if fiscal.get("Type")=="BAL":
                            for fiscal_elm in fiscal:
                                if fiscal_elm.tag == "lineItem":
                                    bal_st[date][fiscal_elm.get("coaCode")]=fiscal_elm.text
                                    
                        if fiscal.get("Type")=="CAS":
                            for fiscal_elm in fiscal:
                                if fiscal_elm.tag == "lineItem":
                                    cs_st[date][fiscal_elm.get("coaCode")]=fiscal_elm.text
                                    
inc_df = pd.DataFrame(inc_st)
inc_df.rename(name_map,inplace=True)

bal_df = pd.DataFrame(bal_st)
bal_df.rename(name_map,inplace=True)

cs_df = pd.DataFrame(cs_st)
cs_df.rename(name_map,inplace=True)
                                    
                                    
                                    
                    