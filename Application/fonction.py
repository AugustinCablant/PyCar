# Imports 
import pandas as pd
import math
from geopy.distance import geodesic
import geopandas as gpd
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import time
import datetime
import pyroutelib3
from pyroutelib3 import Router
import requests, json
import folium 
from CarNetwork import CarNetwork


# Bornes 
URL = 'https://www.data.gouv.fr/fr/datasets/r/517258d5-aee7-4fa4-ac02-bd83ede23d25'
df_bornes = pd.read_csv(URL, sep = ';')

def clean_df(dataframe):
    liste = []
    for row in dataframe.itertuples():
        if row.xlongitude > 90 or row.ylatitude > 90:
            liste.append(row.Index)
    df_bornes = dataframe.drop(liste)
    droping_liste = list(set(df_bornes[df_bornes['xlongitude'].isna()].index.to_list() + df_bornes[df_bornes['ylatitude'].isna()].index.to_list()))
    df = df_bornes.drop(liste)
    return df

def coor_cp(df_code, code_postale):
    for row in df_code.itertuples():
        cp = row.code_postal
        if code_postale == cp:
            lat = row.latitude
            lon = row.longitude
            return [lat, lon]
    return None

def trajet(départ, fin):
        """ 
        Retourne une liste de longitude et 
        de latitude correspondant à la route à suivre pour 
        rejoindre fin depuis départ définis à partir de leur coordonées respectives
        """
        Trajet_lat = []
        Trajet_lon = []
        total = 0
        router = Router('car')
        start = router.findNode(départ[0], départ[1])
        end = router.findNode(fin[0], fin[1])
        status, route = router.doRoute(start, end)
        if status == 'success':
            routeLatLons = list(map(router.nodeLatLon, route))
            for elem in routeLatLons:
                lat, lon = elem
                Trajet_lat.append(lat)
                Trajet_lon.append(lon)
        for i in range(len(Trajet_lat)-1):
            lat_i = Trajet_lat[i]
            lat_f = Trajet_lat[i+1]
            lon_i = Trajet_lon[i]
            lon_f = Trajet_lon[i+1]
            d = geodesic((lat_i, lon_i), (lat_f, lon_f)).km
            total += d
        return Trajet_lat, Trajet_lon, total

def recherche_station_proche(df, dist, lat, lon):
        """ 
        Recherche la station la plus proche dans un périmètre de rayon dist et de centre de coordonnées lat, lon
        """
        lat, lon = np.float(lat), np.float(lon)
        lowest = [0, dist+10]  # index, min distance
        dataframe0 = df.dropna(subset = ['xlongitude', 'ylatitude'])
        index = 0
        for row in dataframe0.itertuples():
            lat_s = row.ylatitude
            lon_s = row.xlongitude
            d = geodesic((lat, lon), (lat_s, lon_s)).km
            if lowest[1] > d:
                lowest[1] = d
                lowest[0] = index
            index += 1

        if lowest[1] > dist:
            return None
        else:
            index = lowest[0]
            ligne = dataframe0.iloc[[index]]
            lat = ligne['ylatitude'].values[0]
            lon = ligne['xlongitude'].values[0]
            nom = ligne['n_enseigne'].values[0]
            return lat, lon, nom
        
def trajet(départ, fin):
    """ 
    Retourne une liste de longitude et 
    de latitude correspondant à la route à suivre pour 
    rejoindre fin depuis départ définis à partir de leur coordonées respectives
    """
    Trajet_lat = []
    Trajet_lon = []
    total = 0
    router = Router('car')
    start = router.findNode(départ[0], départ[1])
    end = router.findNode(fin[0], fin[1])
    status, route = router.doRoute(start, end)
    if status == 'success':
        routeLatLons = list(map(router.nodeLatLon, route))
        for elem in routeLatLons:
            lat, lon = elem
            Trajet_lat.append(lat)
            Trajet_lon.append(lon)
    for i in range(len(Trajet_lat)-1):
        lat_i = Trajet_lat[i]
        lat_f = Trajet_lat[i+1]
        lon_i = Trajet_lon[i]
        lon_f = Trajet_lon[i+1]
        d = geodesic((lat_i, lon_i), (lat_f, lon_f)).km
        total += d
    return Trajet_lat, Trajet_lon, total
        
def trajet_electrique(Trajet_thermique_lat, Trajet_thermique_lon, autonomie):
    """ 
    Pour les véhicules électriques
    """
    Trajet_lat = []
    Trajet_lon = []
    parcourue = 0
    total = 0
    router = Router('car')
    for k in range(len(Trajet_thermique_lat)-1):
        if parcourue <= autonomie*0.7:
            lat_i = Trajet_thermique_lat[k]
            lat_f = Trajet_thermique_lat[k+1]
            lon_i = Trajet_thermique_lon[k]
            lon_f = Trajet_thermique_lon[k+1]

            start = router.findNode(lat_i, lon_i)
            end = router.findNode(lat_f, lon_f)
            status, route = router.doRoute(start, end)
            if status == 'success':
                routeLatLons = list(map(router.nodeLatLon, route))
                for i in range(len(routeLatLons)-1):
                    dep_lat = routeLatLons[i][0]
                    dep_lon = routeLatLons[i][1]
                    fin_lat = routeLatLons[i+1][0]
                    fin_lon = routeLatLons[i+1][1]
                    Trajet_lat.append(dep_lat)
                    Trajet_lat.append(fin_lat)
                    Trajet_lon.append(dep_lon)
                    Trajet_lon.append(fin_lon)
                    d = geodesic((dep_lat, dep_lon), (fin_lat, fin_lon)).km
                    parcourue += d
        else:
            station = recherche_station_proche(df_bornes, autonomie*0.3, Trajet_thermique_lat[k], Trajet_thermique_lon[k])
            if station == None:
                return None
            else:
                lat, lon, nom = station
                start = router.findNode(
                    Trajet_thermique_lat[k], Trajet_thermique_lon[k])
                end = router.findNode(lat, lon)
                status, route = router.doRoute(start, end)
                if status == 'success':
                    routeLatLons = list(map(router.nodeLatLon, route))
                    for i in range(len(routeLatLons)-1):
                        dep_lat = routeLatLons[i][0]
                        dep_lon = routeLatLons[i][1]
                        fin_lat = routeLatLons[i+1][0]
                        fin_lon = routeLatLons[i+1][1]
                        Trajet_lat.append(dep_lat)
                        Trajet_lat.append(fin_lat)
                        Trajet_lon.append(dep_lon)
                        Trajet_lon.append(fin_lon)
                        d = geodesic((dep_lat, dep_lon), (fin_lat, fin_lon)).km
                        parcourue += d
                start = router.findNode(fin_lat, fin_lon)
                end = router.findNode(Trajet_thermique_lat[k], Trajet_thermique_lon[k])
                status, route = router.doRoute(start, end)
                if status == 'success':
                    routeLatLons = list(map(router.nodeLatLon, route))
                    for i in range(len(routeLatLons)-1):
                        dep_lat = routeLatLons[i][0]
                        dep_lon = routeLatLons[i][1]
                        fin_lat = routeLatLons[i+1][0]
                        fin_lon = routeLatLons[i+1][1]
                        Trajet_lat.append(dep_lat)
                        Trajet_lat.append(fin_lat)
                        Trajet_lon.append(dep_lon)
                        Trajet_lon.append(fin_lon)
                        d = geodesic((dep_lat, dep_lon), (fin_lat, fin_lon)).km
                        parcourue += d
            total += parcourue
            parcourue = 0
    total += parcourue
    return Trajet_lat, Trajet_lon, total


class Autoroute(CarNetwork):

    def __init__(self, A, B, autonomie):
        super().__init__(A, B, autonomie)
        self.stations_peages = pd.read_csv('https://static.data.gouv.fr/resources/gares-de-peage-du-reseau-routier-national-concede/20230728-163544/gares-peage-2023.csv', sep = ';')

    
    def clean_base(self):

        ## Dans la base de donnée, les coordonnées des péages sont en 
        #  unité de Lambert 93. Nous les transformons en degrés géographique

        ## Dans la base de donnée, les coordonées de Lambert données dans 
        #  les colonnes 'x' et 'y' sont des strings, on corrige ça 

        self.stations_peages['x'] = self.stations_peages['x'].str.replace(',', '.').astype(float)
        self.stations_peages['y'] = self.stations_peages['y'].str.replace(',', '.').astype(float)


        def lambert93_to_latlon(x, y):

            in_proj = Proj(init='epsg:2154')  # EPSG code for Lambert 93
            out_proj = Proj(init='epsg:4326')  # EPSG code for WGS84 (lat/lon)

            lon, lat = transform(in_proj, out_proj, x, y)
            return lat, lon
                
        ## On crée deux nouvelles colonnes 
        self.stations_peages['xlongitude'] = lambert93_to_latlon(self.stations_peages['x'], self.stations_peages['y'])[0]
        self.stations_peages['ylatitude'] = lambert93_to_latlon(self.stations_peages['x'], self.stations_peages['y'])[1]

        ## On renomme les colonnes par soucis de clarté
        self.stations_peages.rename(columns={'x': 'lambert93_x', 'y' : 'lambert93_y'}, inplace=True)

        '''
        Les coordonnées de longitude > 90 ou de latitude > 90 sont inutiles car elles dépassent les limites 
        des valeurs possibles pour la longitude (de -180 à 180) et la latitude (de -90 à 90) sur la surface 
        de la Terre, et donc, elles sont généralement considérées comme des données incorrectes. 
        La routine supprime ces données du dataframe.
        '''


        liste = []
        for row in self.stations_peages.itertuples():

            if row.xlongitude > 90 or row.ylatitude > 90:
                liste.append(row.Index)

        self.stations_peages.drop(liste)


    def plot_peages_autoroutes(self, map):
        
        ## FAIRE ATTENTION À BIEN APPLIQUER LA MÉTHODE .clean_base() à 
        #  l'objet de la classe Autoroute avant de l'instancier 
        
        df = self.stations_peages[self.stations_peages['route'].str.startswith('A')]

        for index, lat, lon in df[['ylatitude', 'xlongitude']].itertuples():
            
            # attention ici on inverse lon et lat !
            folium.RegularPolygonMarker(location=[lon, lat], color ='blue', radius=5).add_to(map)


################################################################
## FONCTIONS POUR NAÏL ##
################################################################



def cout_distance_thermique(dist, prix_essence, essence = True):
    """ 
    Parameters:
    -----------
    dist : une distance (en kilomètres)
    prix_essence : prix de l'essence à une date t (exemple : 1.8€/l)
    essence : True par défaut (si False, signifie que c'est un véhicule Diesel)
    -----------
    N.B : 
    En 2021, une voiture particulière essence consommait en moyenne 7,54 litres pour parcourir 100 kilomètres 
    contre 6,11 pour les voitures diesel.
    -----------
    return : 
    -----------
    coût pour parcourir la distance 
    """
    if essence == True: 
        conso_100k = 7.54  #nombre de litre consommé par le véhicule à essence sur 100km  
        
    else: 
        conso_100k = 6.11  #nombre de litre consommé par le véhicule disesel sur 100km 
    
    nb_litre_trajet = (dist * conso_100k) / 100  #nombre de litre consommé par le véhicule sur la distance dist 
    cout_trajet = nb_litre_trajet * prix_essence  #coût du trajet 
    return cout_trajet 



def cout_trajet_electrique(start, autonomie_véhicule, autonomie_start, dist, liste_localisation_bornes, prix):
    """ 
    Parameters:
    -----------
    start : [lat, lon] point de départ du véhicule électrique
    autonomie_véhicule : autonomie du véhicule si rechargé à 100% (exemple : 500km)
    autonomie_start : autonomie du véhicule au départ (exemple : 200km)
    dist : distance que le véhicule souhaite parcourir
    liste_localisation_bornes : liste contenant la localisation des bornes et le prix du kWH sur lesquelles le véhicule va s'arrêter
    pour se recharger (chaque élément de la liste est un triplet du type : [lat, lon, prix])
    conso : conso du véhicule (exemple : 17 kWh/100 km)
    prix : prix du kWh (exemple : 0.50€)
    -----------
    N.B : 
    Un véhicule électrique consomme entre 15 et 18 kWh pour effectuer 100 km en milieu urbain et extra-urbain. 
    Et consomme 20 à 25 kWh pour 100 km parcourus sur autoroute.
    -----------
    Return : 
    -----------
    coût pour qu'à la fin du voyage, le véhicule soit rechargé à 100% 
    """
    cout_total = 0
    for i, sous_liste in enumerate(liste_localisation_bornes): 
        prix_borne = sous_liste[2]
        if i==0:
            distance = distance_entre_2_bornes(start, sous_liste[0:2])  #distance entre le point de départ et la borne 1
        else: # i > 0
            sous_liste_avant = liste_localisation_bornes[i-1]
            borne_avant = sous_liste_avant[0:2]  #[lat, lon]
            distance = distance_entre_2_bornes(borne_avant, sous_liste[0:2])  #distance entre la borne i-1 et i
        autonomie_restante = autonomie_start - distance
        if autonomie_restante<=0:
            print(f"Le trajet trouvé n'est pas le bon, le véhicule tombe en panne avant d'avoir pu atteindre la borne {i}")
        else: 
            nb_km_remplir = autonomie_véhicule - autonomie_restante  #nb de km qu'il faut pour que le véhicule ait une autonomie max
            prix_100km = 20 * prix  #on suppose que le véhicule roule sur une autoroute (donc 20kwH pour 100km)
            cout_auto_max = (nb_km_remplir * prix_100km) / 100  #prix pour que le véhicule soit à son autonomie maximale
            cout_total += cout_auto_max  #actualisation du coût total
    return cout_total