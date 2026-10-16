#!/usr/bin/env python
# coding: utf-8

# In[ ]:


# reanalyses of annual carbon emissions by terrestrial data centers (DC)
# for detials see section 1 of "Supplementary Notes" of the paper

from matplotlib import pyplot as plt
import numpy as np
from matplotlib.ticker import AutoMinorLocator
import json
from pathlib import Path

script_dir = Path(__file__).resolve().parent

    
with open(script_dir/'Google_DC_emisssions.json', 'r') as openfile:
    paramaters = json.load(openfile)
 
print(paramaters)


# In[ ]:


# compute ratio of scope 1 energy consumptions (E_s1, fuel) to scope 2 energy consumption (E_s2, purchaased electrcity)
#%matplotlib qt

figure = plt.figure()
plt.title('Scope 1 to scope 2 energy ratio', family = 'arial',fontsize = 20)
    
for index, item in paramaters.items():  
    item['Es1_to_Es2_ratio_annual'] = [np.round(i/j, 2) for i, j in zip(item['fuel'], item['purchased_electricity'])]
    item['Es1_to_Es2_ratio_average'] = np.round(sum(item['fuel'])/sum(item['purchased_electricity']), 2)
        
    print(index,'Es1_to_Es2_ratio_annual\n', item['Es1_to_Es2_ratio_annual'], '\n')
    print(index, 'Es1_to_Es2_ratio_average\n', item['Es1_to_Es2_ratio_average'],'\n')
    

    plt.plot(item['years'], item['Es1_to_Es2_ratio_annual'], 'o--', color = 'tab:orange', linewidth=2, markersize=12, label=index)

plt.xlim([2018.8, 2022.2])
plt.ylim([0, 0.1])
plt.xticks(item['years'], family = 'arial', fontsize=20, rotation = 0)
plt.yticks(np.arange(0, 0.11, step=0.02), family = 'arial', fontsize=20,  rotation = 0)
plt.gca().yaxis.set_minor_locator(AutoMinorLocator(2))
plt.gca().set_position([0.2, 0.2, 0.7, 0.6])

font = {'family': 'arial',
        'color':  'black',
        'weight': 'normal',
        'size': 20,
        }
plt.xlabel('Year',fontdict=font)
plt.ylabel('$E_{s1}/E_{s2}$', fontdict=font)

plt.legend({r'$\frac{E_{s1}}{E_{s2}}$'},loc='center right', prop = {'family' : 'arial','size' : 25}, frameon=False)

# plt.show()
plt.close()


# In[ ]:


# compute carbon intensity of scope 1 energy consumption: I_s1 = C_s1/E_s1 (C_s1, from fuel; c_s2, from electrcity)

figure = plt.figure()
plt.title('Scope 1 carbon intensity (g/kWh)', family = 'arial',fontsize = 20)
    
for index, item in paramaters.items():  
    item['scope1_carbon_intensity'] = [np.round(1000*i/j, 0) for i, j in zip(item['scope1_emissions'], item['fuel'])] # in g/kWH
    item['scope1_carbon_intensity_average'] = np.round(1000*sum(item['scope1_emissions'])/sum(item['fuel']), 0) # in g/kWH
        
    print(index,'scope1_carbon_intensity\n', item['scope1_carbon_intensity'], '\n')
    print(index, 'scope1_carbon_intensity_average\n', item['scope1_carbon_intensity_average'],'\n')
    
    plt.plot(item['years'], item['scope1_carbon_intensity'], 'o--', color = 'tab:orange',  linewidth=2, markersize=12, label=index)
    

plt.xlim([2018.8, 2022.2])
plt.ylim([0, 300])
plt.xticks(item['years'], family = 'arial', fontsize=20, rotation = 0)
plt.yticks(np.arange(0, 301, step=50), family = 'arial', fontsize=20,  rotation = 0)
plt.gca().yaxis.set_minor_locator(AutoMinorLocator(2))
plt.gca().set_position([0.2, 0.2, 0.7, 0.6])

font = {'family': 'arial',
        'color':  'black',
        'weight': 'normal',
        'size': 20,
        }
plt.xlabel('Year',fontdict=font)
plt.ylabel('$I_{s1} \ (gCO_2e/kWh)$', fontdict=font)

plt.legend({'$I_{s1}$ $(gCO_2/kWh)$'},loc='lower right', prop = {'family' : 'arial','size' : 20}, frameon=False)
# plt.show()
plt.close()


# In[ ]:


# compute scope 2 carbon intensity in g/kWH: I_s2

figure = plt.figure()
plt.title('Scope 2 carbon intensity (g/kWh)', family = 'arial',fontsize = 20)

for index, item in paramaters.items():  
    item['scope2_carbon_intensity'] = [np.round(1000*i/j,0) for i, j in zip(item['scope2_emissions_location_based'], item['purchased_electricity'])] # in g/kWH
    item['scope2_carbon_intensity_average'] = np.round(1000*sum(item['scope2_emissions_location_based'])/sum(item['purchased_electricity']),0) # in g/kWH
    
    print(index,'scope2_carbon_intensity\n', item['scope2_carbon_intensity'], '\n')
    print(index, 'scope2_carbon_intensity_average\n', item['scope2_carbon_intensity_average'],'\n')
    
    plt.plot(item['years'], item['scope2_carbon_intensity'], 'o--', color = 'tab:orange', linewidth=2, markersize=12, label=index)
    
plt.xlim([2018.8, 2022.2])
plt.ylim([0, 500])
plt.xticks(item['years'], family = 'arial', fontsize=20, rotation = 0)
plt.yticks(np.arange(0, 501, step=100), family = 'arial', fontsize=20,  rotation = 0)
plt.gca().yaxis.set_minor_locator(AutoMinorLocator(2))
plt.gca().set_position([0.2, 0.2, 0.7, 0.6])

font = {'family': 'arial',
        'color':  'black',
        'weight': 'normal',
        'size': 20,
        }
plt.xlabel('Year',fontdict=font)
plt.ylabel('$I_{s2} \ (gCO_2e/kWh)$', fontdict=font)

plt.legend({'$I_{s2}$ $(gCO_2/kWh)$'},loc='lower right', prop = {'family' : 'arial','size' : 20}, frameon=False)
# plt.show()
plt.close()
    


# In[ ]:


# compute ratio of scope 3 onetime to  scope 2 energy consumptions: onetime - capital goods + upstream transporation

I_s3_ref = 271/1000 # in kg/kWh or t/MWh, reference carbon intensity of energy accross scope 3 eneryg consumptions

figure = plt.figure()
plt.title('scope 3 to scope 2 energy ratio:\n onetime (capital + transport)', family = 'arial',fontsize = 20)
    
for index, item in paramaters.items():
    item['scope3_emisssions_onetime'] = [(i+j) for i, j in zip(item['scope3_emisssion_capial_goods'],                                                               item['scope3_emisssion_upstream_transporaion'])]
    
    item['scope3_carbon_intensity'] = I_s3_ref*1000; # in g/kWh
    
    item['Es3_onetime_to_E2_ratio_annual'] = [np.round(i/I_s3_ref/j, 2) for i,j in zip(item['scope3_emisssions_onetime'],                                                                    item['purchased_electricity'])]                                                                     
    item['Es3_onetime_to_E2_ratio_average'] = np.round(sum(item['scope3_emisssions_onetime'])/I_s3_ref                                                /sum(item['purchased_electricity']),2)
        
    print(index,'Es3_onetime_to_E2_ratio_annual\n', item['Es3_onetime_to_E2_ratio_annual'], '\n')
    print(index, 'Es3_onetime_to_E2_ratio_average\n', item['Es3_onetime_to_E2_ratio_average'],'\n')

    plt.plot(item['years'], item['Es3_onetime_to_E2_ratio_annual'], 'o--', color = 'tab:orange', linewidth=2, markersize=12, label=index)

plt.xlim([2018.8, 2022.2])
plt.ylim([0, 1])
plt.xticks(item['years'], family = 'arial', fontsize=20, rotation = 0)
plt.yticks(np.arange(0, 1.1, step=0.2), family = 'arial', fontsize=20,  rotation = 0)
plt.gca().yaxis.set_minor_locator(AutoMinorLocator(2))
plt.gca().set_position([0.2, 0.2, 0.7, 0.6])

font = {'family': 'arial',
        'color':  'black',
        'weight': 'normal',
        'size': 20,
        }
plt.xlabel('Year',fontdict=font)
plt.ylabel(r'$E_{s3,onetime}/E_{s2}$', fontdict=font)

plt.legend({r'$\frac{E_{s3, onetime}}{E_{s2}}$'},loc='upper right', prop = {'family' : 'arial','size' : 25}, frameon=False)
# plt.show()
plt.close()


# In[ ]:


# compute ratio of scope 3 to scope 2 energy consumptions : scope 3 reccurrent emissions (all others)

figure = plt.figure()
plt.title('scope 3 to scope 2 energy ratio:\n reccurent', family = 'arial',fontsize = 20)
    
for index, item in paramaters.items():
    item['scope3_emisssions_recurrent'] = [(m-(i+j)) for m, i, j in zip(item['scope3_emissions'],                                                                        item['scope3_emisssion_capial_goods'],                                                                        item['scope3_emisssion_upstream_transporaion'])]
    item                                                                            
    item['Es3_recurrent_to_E2_ratio_annual'] = [np.round(i/I_s3_ref/j,2) for i, j in zip(item['scope3_emisssions_recurrent'],                                                                       item['purchased_electricity'])]
                                                                                    
    item['Es3_recurrent_to_E2_ratio_average'] = np.round(sum(item['scope3_emisssions_recurrent'])/I_s3_ref                                                   /sum(item['purchased_electricity']),2)
        
    print(index,'Es3_recurrent_to_E2_ratio_annual\n', *item['Es3_recurrent_to_E2_ratio_annual'], '\n')
    print(index, 'Es3_recurrent_to_E2_ratio_average\n', item['Es3_recurrent_to_E2_ratio_average'],'\n')
    

    plt.plot(item['years'], item['Es3_recurrent_to_E2_ratio_annual'], 'o--', color = 'tab:orange', linewidth=2, markersize=12, label=index)

plt.xlim([2018.8, 2022.2])
plt.ylim([0, 3])
plt.xticks(item['years'], family = 'arial', fontsize=20, rotation = 0)
plt.yticks(np.arange(0, 3.1, step=0.5), family = 'arial', fontsize=20,  rotation = 0)
plt.gca().yaxis.set_minor_locator(AutoMinorLocator(2))


font = {'family': 'arial',
        'color':  'black',
        'weight': 'normal',
        'size': 20,
        }
plt.xlabel('Year',fontdict=font)
plt.ylabel('$E_{s3,recurrent}/E_{s2}$', fontdict=font)

plt.legend({r'$\frac{E_{s3, recurrent}}{E_{s2}}$'},loc='upper right', prop = {'family' : 'arial','size' : 25}, frameon=False)
# plt.show()
plt.close()


# In[ ]:


# avarage power usage effectinvess (PUE)
for index, item in paramaters.items():
    item['PUE_average'] = round(sum(item['PUE'])/len(item['PUE']),2)
    print(item['PUE_average'])
    


# In[ ]:


# lifecycle CUE in g/kWh

for index, item in paramaters.items():
    total_emisssons = sum([sum(item['scope1_emissions']),                          sum(item['scope2_emissions_location_based']),                          sum(item['scope3_emissions'])]) # total emissosn accross all three scopes over 4 years
    total_electricity = sum(item['purchased_electricity']) # total electric energy consumptions over 4 years
    item['Lifecycle_CUE'] = np.round(1000*item['PUE_average']*total_emisssons/total_electricity,0) # in g/kWh
    
print('Lifecycle CUE of Google is:', item['Lifecycle_CUE'])


# In[ ]:


# save reanalized data

json_object = json.dumps(paramaters, indent=4)
with open(script_dir/"Google_DC_emissions_reanalysis.json", "w") as outfile:
    outfile.write(json_object)

# print
for key1, item in paramaters.items():
    print(key1, ':')
    for key2, item2 in paramaters[key1].items():
        print('\n\t',key2, ':')
        print('\t', item2, sep = '\n\t\t')

