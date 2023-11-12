# Imports 
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import pyroutelib3
from pyroutelib3 import Router
import requests, json
import urllib.parse
import folium 
import geopy.distance 
from geopy.distance import geodesic
from folium.plugins import MousePosition
from folium.plugins import TagFilterButton




# Coordonnées des villes en France 

# Liste des colonnes de df : ['insee_code', 'city_code', 'zip_code', 'label', 'latitude', 'longitude', 
#                            'department_name', 'department_number', 'region_name', 'region_geojson_name']


class CarNetwork():
    """
    Classe qui calcul le trajet optimal pour relier un point A à un point B avec une voiture électrique en France.

    Parameters:
    -----------
    A : adresse de départ  / format : numéro, rue, code postal ville (en minuscule)
    B : adresse d'arrivée / format : numéro, rue, code postal ville (en minuscule)
    Autonomie : Autonomie du véhicule utilisé
    --> on précise l'autonomie car si celle-ci est supérieure à la distance totale, 
    alors rien ne sert d'optimiser le trajet.

    Attributes:
    -----------
    x_A : (latitude, longitude) du point A
    x_B : (latitude, longitude) du point B
    df : base de données sur laquelle repose la classe. On la défini à partir d'un URL

    Methods:
    --------
    get_coordo : permet de récupérer x_A et x_B
    calcul_distance_haversine : permet de calculer une distance à vol d'oiseau
    """

    def __init__(self, A, B, autonomie):
        self.A = A
        self.B = B
        self.autonomie = autonomie
        self.x_A = None
        self.x_B = None
        self.stations_data = pd.read_csv('https://www.data.gouv.fr/fr/datasets/r/517258d5-aee7-4fa4-ac02-bd83ede23d25', sep = ';')

    def clean_data(self):
        '''
        Les coordonnées de longitude > 90 ou de latitude > 90 sont inutiles car elles dépassent les limites 
        des valeurs possibles pour la longitude (de -180 à 180) et la latitude (de -90 à 90) sur la surface 
        de la Terre, et donc, elles sont généralement considérées comme des données incorrectes. 
        La routine supprime ces données du dataframe.
        '''

        liste = []
    
        for row in self.stations_data.itertuples():

            if row.xlongitude > 90 or row.ylatitude > 90:
                liste.append(row.Index)

        self.stations_data.drop(liste)

        # we clean the dataframe 

        droping_liste = list(set(self.stations_data[self.stations_data['xlongitude'].isna()].index.to_list() + self.stations_data[self.stations_data['ylatitude'].isna()].index.to_list()))
        self.stations_data.drop(droping_liste, inplace = True)

        # we transform the acces row in the dataframe by defining 
        # a function that we will then apply to the "acces_recharge" row

        def transform_acces(row):
            if not pd.isna(row):  # On ne peut rien dire des nan
                row = row.lower()  # Mettre en lettre minuscule 
                mots = row.split(' ')
                if 'payant' in mots: row = 'payant'
                elif 'gratuit' in mots: row = 'gratuit'
                for mot in mots: 
                    if len(mot.split('€'))>1: row = 'payant'
                    if mot=='carte' or mot=='badge': row = 'carte ou badge'
                    if mot=='oui': row = 'information manquante'
                #else: row = 'accès spécial'
            else: row = 'information manquante'
            return row
        
        self.stations_data['acces_recharge'] = self.stations_data['acces_recharge'].apply(transform_acces)
        list(self.stations_data['acces_recharge'].unique())


    def get_coordo(self):
        """
        Permet de renvoyer (latitude,longitude)
        """
        dep_json_A = requests.get("https://api-adresse.data.gouv.fr/search/?q=" + urllib.parse.quote(self.A) + "&format=json").json()
        dep_json_B = requests.get("https://api-adresse.data.gouv.fr/search/?q=" + urllib.parse.quote(self.B) + "&format=json").json()
        self.x_A = list(dep_json_A['features'][0].get('geometry').get('coordinates'))
        self.x_B = list(dep_json_B['features'][0].get('geometry').get('coordinates'))


    def trajet_voiture(self):
    

        """
        ================================================================
        IDÉE : Fonction qui calcule l'itinéraire en voiture entre deux 
               adresses en utilisant l'API d'adresse gouvernementale et 
               la bibliothèque pyroutelib3.

        ================================================================

        ================================================================
        PARAMÈTRES : 

        ================================================================

        ================================================================
        SORTIE : Liste de coordonnées (latitude, longitude) représentant 
                 l'itinéraire en voiture.
        ================================================================

        
        
        Note: Il est recommandé d'inclure le code de la fonction get_cordo dans cette routine au cas où
        l'utilisateur utilise la méthode trajet_voiture avant celle get_cordo. Dans ce cas, les transformations
        sur self.x_A et self.x_B n'auraient pas été faites.

        """


        ## Il faut inclure le code de get_cordo dans le code de cette routine au cas où l'utilisateur 
        # utilise la méthode trajet_voiture avant celle get_cordo auquel cas les transformations sur 
        # self.x_A et self.x_B n'auraient pas été faites. 

        dep_json_A = requests.get("https://api-adresse.data.gouv.fr/search/?q=" + urllib.parse.quote(self.A) + "&format=json").json()
        dep_json_B = requests.get("https://api-adresse.data.gouv.fr/search/?q=" + urllib.parse.quote(self.B) + "&format=json").json()
        self.x_A = list(dep_json_A['features'][0].get('geometry').get('coordinates'))
        self.x_B = list(dep_json_B['features'][0].get('geometry').get('coordinates'))

        coord_dep = self.x_A 
        coord_arr = self.x_B
        router = pyroutelib3.Router('car')
        depart = router.findNode(coord_dep[1], coord_dep[0])
        #print(depart)
        arrivee = router.findNode(coord_arr[1], coord_arr[0])
        #print(arrivee)

        routeLatLons=[coord_dep,coord_arr]

        status, route = router.doRoute(depart, arrivee)

        if status == 'success':
            #print("Votre trajet existe")
            routeLatLons = list(map(router.nodeLatLon, route))
        #else:
            #print("Votre trajet n'existe pas")

        return routeLatLons
    
    def get_route_map(self):

        """

        ================================================================
        IDÉE : Fonction qui génère une carte représentant l'itinéraire 
               en voiture entre deux destinations, centrée sur Paris, 
               avec l'itinéraire tracé en rouge.
        ================================================================

        ================================================================
        PARAMÈTRES : 

        ================================================================

        ================================================================
        SORTIE : Objet carte Folium représentant l'itinéraire.
        ================================================================

        """

        trajet = self.trajet_voiture()
        paris_coord = [48.8566, 2.3522]

        # Crée une carte centrée sur Paris
        carte = folium.Map(location=paris_coord, zoom_start=13)

        # Trace l'itinéraire
        """folium.PolyLine(locations=trajet, color='red').add_to(carte)"""

        folium.plugins.AntPath(
            locations=trajet, 
            reverse="True", 
            dash_array=[20, 30]
        ).add_to(carte)

        carte.fit_bounds(carte.get_bounds())

        # Paramétrer le plein écran sur la carte
        folium.plugins.Fullscreen(
            position="bottomleft",
            title="Expand me",
            title_cancel="Exit me",
            force_separate_button=True,
        ).add_to(carte)
        
        # Permet à l'utilisateur d'afficher la localisation du point sur 
        # lequel sa souris pointe
        MousePosition().add_to(carte)

    

        # Affiche la carte dans le notebook
        return carte
    
    def distance_via_routes(self):

        """

        ================================================================
        IDÉE : Fonction qui calcule la distance totale d'un trajet en 
               voiture entre deux destinations, tout en identifiant les 
               points d'arrêt potentiels où l'autonomie de la voiture ne 
               suffit plus.
        ================================================================

        ================================================================
        PARAMÈTRES : 

        ================================================================

        ================================================================
        SORTIE : Tuple contenant la distance totale du trajet en voiture 
                 et une liste de coordonnées représentant les points 
                 d'arrêt potentiels où l'autonomie de la voiture ne suffit 
                 plus.
        ================================================================

        """

        ## On récupère le trajet en voiture entre les deux destinations 
        # A et B
        trajet = self.trajet_voiture()

        distance = 0
        distance_1 = 0 ## we use this double variable in the if
        # condition to remove the autonomy
        j = 0

        stop_coord = []

        for i in range(len(trajet)-1):
        
            ## on convertit l'élément i de la liste trajet, 
            # qui est un tuple, en une liste
            trajet_depart = list(trajet[i]) 
            trajet_arrivee = list(trajet[i+1])

            d = geopy.distance.distance(trajet_depart, trajet_arrivee).kilometers

            distance = distance + d
            distance_1 = distance 
            distance_1 = distance_1 - j*self.autonomie

            ## On fait d'une pierre deux coup dans ce code en calculant 
            #  une liste qui renvoie les premiers points à partir desquels 
            #  l'autonomie ne couvre plus la distance. 

            if self.autonomie < distance_1:
                stop_coord.append(list(trajet[i]))
                j = j + 1 # compte combien de fois l'autonomie a été saturée pour pénaliser 
                          # la distance_1 sur toutes les boucles à partir de là

        
        return distance, stop_coord
    
    def plot_stop_points(self, map):

        """

        ================================================================
        IDÉE : Fonction pour représenter graphiquement sur une carte les 
               points d'arrêt du réseau, en utilisant des marqueurs de 
               couleur violette.
        ================================================================

        ================================================================
        PARAMÈTRES : 

        -map : Objet carte Folium sur laquelle les points d'arrêt seront 
               représentés.

        ================================================================

        ================================================================
        SORTIE : La carte Folium mise à jour avec des marqueurs violets 
                 représentant les points d'arrêts les plus proches.
        ================================================================

        """

        # Appel à la fonction distance_via_routes pour obtenir les distances et les coordonnées des points d'arrêt
        distance, stop_coord = self.distance_via_routes()

        # Itération sur chaque point d'arrêt
        for i in range(len(stop_coord)):
            lat = stop_coord[i][0]
            lon = stop_coord[i][1]


            folium.Marker(
                location=[lat, lon],
                icon=folium.Icon(color='purple'),
                popup=f"Arrêt numéro {i} : vous devez recharger votre batterie.",
                ).add_to(map)


    def nearest_stations(self, stop_coord, distance_max): 

        """

        ================================================================
        IDÉE : Fonction qui identifie et renvoie les stations les plus 
               proches pour chaque point d'arrêt donné,dans une plage de 
               distance spécifiée.
        ================================================================

        ================================================================
        PARAMÈTRES : 

        -stop_coord : Liste des coordonnées (latitude, longitude) des 
                      points d'arrêt. Tel que rendu par distance_via_routes

        -distance_max : Distance maximale (en kilomètres) à partir de 
                        laquelle une station est considérée comme "proche".
        ================================================================

        ================================================================
        SORTIE : Liste de listes, où chaque sous-liste représente les 
                 coordonnées des stations les plus proches pour un point 
                 d'arrêt donné.
        ================================================================

        """

        # Extraction des coordonnées des stations du DataFrame self.stations_data
        stations = self.stations_data[['xlongitude', 'ylatitude']]
        stations = stations[(stations['ylatitude'] >= -90) & (stations['ylatitude'] <= 90) &
            (stations['xlongitude'] >= -90) & (stations['xlongitude'] <= 90)]

        ## On récupère uniquement les données qui nous intéressent sous forme 
        # de tuple de localisations (latitude, longitude)   
        loc_tuples = [(row.ylatitude, row.xlongitude) for row in stations.itertuples()]
    
        ## on définit une lambda fonction qui prend en argument une distance, 
        # un couple (latitude, longitude) [dans coord] et un float distance_max
        # et qui teste si la distance entre location et coord est inférieure (renvoie
        # alors True) à la distance_max
        is_in_range = lambda location, coord, distance: geodesic(location, coord).kilometers <= distance


        ## On instancie une liste vide qu'on remplira des stations les plus proches pour chaque 
        # point d'arrêt
        nearest_stations = []
        for i in range(len(stop_coord)):

            location = stop_coord[i]
                   
            # Filtrage des stations qui sont dans la plage de distance pour le point d'arrêt actuel
            location_tuples = [list(element) for element in loc_tuples if is_in_range(location, element, distance_max)]

            # Ajout des stations filtrées à la liste des stations les plus proches
            nearest_stations.append(location_tuples)

        return nearest_stations

    def plot_nearest_stations(self, map, nearest_stations):

        """ 
        ================================================================
        IDÉE : Fonction permettant de représenter graphiquement sur une 
               carte toutes les stations les plus proches associées à des 
               points d'arrêt donnés.
        ================================================================

        ================================================================
        PARAMÈTRES : 

        -map : objet de type folium map, tel que renvoyé par get_route_map
               ou plot_stop_points

        -nearest_stations : liste de longueur égale au nombre d'arrêt 
                            sur le trajet. Chaque élément correspond 
                            lui-même à une liste de liste contenant les 
                            localisations des stations les plus proches
        ================================================================

        ================================================================
        SORTIE : La carte Folium mise à jour avec des marqueurs représentant 
                 les stations les plus proches.
        ================================================================

        """
         
        for i in range(len(nearest_stations)):
    
            ## On récupère les localisations de toutes les bornes les 
            # plus proches du i-ème point d'arrêt 
            nearest_stations_i = nearest_stations[i]

            ## On itère sur cette première liste pour représenter toutes les
            # stations les plus proches 
            for j in range(len(nearest_stations_i)):
                lat = nearest_stations_i[j][0] ## longitude
                lon = nearest_stations_i[j][1] ##  latitude

                folium.Marker(
                location=[lat, lon],
                icon=folium.Icon(color='yellow'),
                popup=f"Ceci est l'une des {len(nearest_stations_i)} bornes les plus proches de l'arrêt numéro {i}.",
                ).add_to(map)

    def plot_stations(self, map):

        """ 
        ================================================================
        IDÉE : Fonction permettant de représenter graphiquement sur une 
               carte folium toutes les stations dont on dispose dans notre 
               base de données en attribut.
        ================================================================

        ================================================================
        PARAMÈTRES : 

        -map : objet de type folium map, tel que renvoyé par get_route_map
               ou plot_stop_points

        ================================================================

        ================================================================
        SORTIE : La carte Folium mise à jour avec des marqueurs représentant 
                 toutes les stations de recharge de véhicules électrique en 
                 France.
        ================================================================

        """

        ## On récupère les données sur lesquelles on travaille
        df = self.stations_data


        legend_html = """
        <div style="position: fixed; 
                    top: 10px; 
                    right: 10px; 
                    width: 220px; 
                    background-color: rgba(255, 255, 255, 0.8); 
                    border: 2px solid #000; 
                    border-radius: 5px; 
                    box-shadow: 3px 3px 5px #888; 
                    z-index: 1000; padding: 10px; font-size: 14px; font-family: Arial, sans-serif;">
            <p style="text-align: center; font-size: 18px;"><strong>Légende de la Carte</strong></p>
            
            <p><i class="fa fa-square" style="color: orange;"></i> <strong>Payant</strong></p>
            
            <p><i class="fa fa-square" style="color: green;"></i> <strong>Gratuit</strong></p>
            
            <p><i class="fa fa-square" style="color: grey; font-size: 20px;"></i> <strong>Informations manquantes</strong></p>
            
            <p><i class="fa fa-square" style="color: cyan; font-size: 20px;"></i> <strong>Carte ou badge</strong></p>
            
            <p><i class="fa fa-square" style="color: yellow; font-size: 20px;"></i> <strong>Gratuit de 12-14h et de 19h-21h</strong></p>
            
            <p><i class="fa fa-map-marker" style="color: purple; font-size: 20px;"></i> <strong>Points d'arrêt</strong></p>
        </div>
        """

        # Ajoutez la légende personnalisée à la carte
        map.get_root().html.add_child(folium.Element(legend_html))


        for index, lat, lon, com, acces_recharge in df[['ylatitude', 'xlongitude', 'n_station', 'acces_recharge']].itertuples():
            # Créez un marqueur avec une couleur différente en fonction des valeurs
            if acces_recharge == 'payant': fill_color = 'orange'
            elif acces_recharge == 'gratuit': fill_color = 'green'
            elif acces_recharge == 'information manquante': fill_color = 'grey'
            elif acces_recharge == 'carte ou badge': fill_color = 'cyan'
            elif acces_recharge == 'charges gratuites de 12 à 14h et de 19h à 21h': fill_color = 'yellow'

            # Ajoutez le marqueur à la carte
            folium.RegularPolygonMarker(location=[lat, lon], 
                                        tags = acces_recharge,
                                        popup=com, 
                                        fill_color=fill_color, 
                                        color =fill_color, 
                                        radius=5
                                        ).add_to(map)

        categories = list(df['acces_recharge'].unique())
        TagFilterButton(categories).add_to(map)


