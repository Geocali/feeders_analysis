#!/usr/bin/python


from python_ltspice_tools import *
import pandas as pd
import re


# -----------------------------------------
#On fait tourner un modèle existant en simulant l'avancée de camions
class simu_camions:
    def param_from_model(self, path):
        # Pour connaître la longueur de la plateforme, 
        # - on compte le nombre de CA
        # - on récupère le nombre de rails par CA
        # - on récupère la longueur d'un rail
        fichier  = open(path, "r")
        tab = fichier.readlines()
        nb_ca = 0
        for line in tab:
            # on compte le nombre de CA
            nb_ca = nb_ca + line.count("CA_v1")
            
            if line.count("L_rail=") > 0:
                tab_tmp = line.split(" ")
                for elmt in tab_tmp:
                    # on récupère la longueur d'un rail
                    if elmt.count("L_rail=")>0:
                        L_rail = float(elmt.split("=")[1]*1)
                    # on récupère le nombre de rails par CA
                    if elmt.count("Nb_rails=")>0:
                        Nb_rails = float(elmt.split("=")[1]*1)
            
        d_plateforme = nb_ca * Nb_rails * L_rail
        return (nb_ca, L_rail, Nb_rails, d_plateforme)
    
    def place_camions_ini(self):
        # on place les camions au temps t=0
        d_camions = []
        d0 = 0
        d = d0
        while d < self.d_plateforme:
            d_camions.append(d)
            d = d + self.d_camion
        return d_camions
    
    def param_camions_t(self, t):
        d_camions = self.d_camions0
        # on calcule la position des camions au temps t
        for i in range(len(d_camions)):
            d_camions[i] = d_camions[i] + self.v_camion * t
        # on ajoute les camions en début de plateforme
        d_min = min(d_camions)
        while d_min - self.d_camion > 0:
            d_camions.append(d_min - self.d_camion)
            d_min = min(d_camions)
        d_camions.sort()
        # on enlève les camions qui ont quitté la plateforme
        d_camions = list(filter(lambda x : x <= self.d_plateforme, d_camions))

        # on compte le nombre de camions sur chaque CA
        nb_camions_sur_ca = []
        for i in range(self.nb_ca):
            d_ca_min = i * self.Nb_rails * self.L_rail
            d_ca_max = (i + 1) * self.Nb_rails * self.L_rail
            nb = sum((x >= d_ca_min and x < d_ca_max) for x in d_camions)
            nb_camions_sur_ca.append(nb)

        # pour chaque CA, on ajuste la résistance correspondant au nombre de camions
        change_params = {}
        for i in range(self.nb_ca):
            nom_resistance = "Rtruck" + str(i + 1)
            if(nb_camions_sur_ca[i]) == 0:
                change_params[nom_resistance] = "R_vide"
            else:
                change_params[nom_resistance] = str(nb_camions_sur_ca[i]) + "*R_truck"
        return change_params
        
    def lancer_simu(self, change_params):
        # on lance la simulation pour ces nouveaux paramètres
        new_netlist = self.original_netlist.change_parameters(change_params)

        #Run the new netlist and store the results in a raw_value object
        new_raw_values = new_netlist.run_netlist()
        
        resultats = []
        for node, node_value in new_raw_values.node_values.items():
            #test = .5 #s
            #result = self.raw_values.find_node_value_at_independet_value(given_independent_value=test,given_node=node_value)
            #print(node,result)
            if(node != 'time'):
                # dans le cas d'un point, on récupère sa tension
                resultats.append([node_value.node, node_value.node_number, node_value.node_type, node_value.values[0]])
                #resultats.append([node, result[0], result[1]])
                
        df = pd.DataFrame(resultats, columns=['nom_point', 'nb_point', 'type_valeur', 'valeur'])
        return df
        
    def __init__(self, chemin_modele):
        self.original_netlist = netlist_class(chemin_modele.replace("asc", "net"))
        self.raw_values = self.original_netlist.run_netlist()
    
        # Vitesse moyenne des camions :
        self.v_camion = 100 / 3.6 # m/s

        # Distance moyenne entre l'avant de deux camions :
        self.d_camion = 50 + 17 # m (distance minimale autoroute=50m, longueur camion = 17m)
        
        # on récupère les paramètres du modèle
        (self.nb_ca, self.L_rail, self.Nb_rails, self.d_plateforme) = self.param_from_model(chemin_modele)
        
        # on place les camions à t=0
        self.d_camions0 = self.place_camions_ini()
        
        # boucle sur le temps
        duree = 60 # secondes
        resultats = []
        for t in range(0, duree):
            print(str(t + 1) + "/" + str(duree))
        
            # on adapte la position des camions
            change_params = self.param_camions_t(t)
            
            # on lance la simulation
            resultats_tmp = self.lancer_simu(change_params)
            resultats_tmp['t'] = pd.Series(t, index=resultats_tmp.index)
            resultats.append(resultats_tmp)
        
        # on joint tous les tableaux
        resultats = pd.concat(resultats)
        # on ne garde que les feeders
        i_feeders = resultats[resultats['nom_point'].str.contains("Ra_")]
        i_feeders = i_feeders[['nom_point', 't', 'valeur']]
        # on fait une colonne pour chaque feeder
        nom_feeders = i_feeders.nom_point.unique()
        tableau_final = pd.DataFrame()
        # on ajoute une colonne avec le temps
        tableau_final['t'] = [i + 1 for i in range(duree)]
        for nom in nom_feeders:
            tableau_final[nom] = i_feeders.loc[i_feeders['nom_point'] == nom]['valeur'].values
        # on prend les valeurs absolues des courants
        tableau_final = tableau_final.apply(abs)
        tableau_final.to_csv("courants_feeder.csv", sep=";", index=False)
        
        
# -----------------------------------------

simulation = simu_camions("C:/_data_cv/ERS/CV/System sizing/simulation/CA_sur_feeders.asc")