from flask import Flask, render_template, request
import matplotlib.pyplot as plt
from io import BytesIO
import base64
from graphiques import evolution_nbre_voiture_elec
#from CarNetwork import CarNetwork


app = Flask(__name__)

@app.route('/')
def accueil():
    return '''
    <html>
    <head>
        <title>Calcul d'autonomie pour un voyage en France</title>
        <style>
            body {
                text-align: center;
            }
        </style>
    </head>
    <body>
        <h1>Bienvenue sur notre application PyCar</h1>
        <h2>Le premier calculateur d'itinéraire pour un véhicule électrique prenant en compte les bornes de recharge présentes sur le territoire français</h2>
        <form method="post" action="/calcul">
            <label for="destination">Destination en France :</label>
            <input type="text" id="destination" name="destination"><br>
            <label for="depart">Point de départ :</label>
            <input type="text" id="depart" name="depart"><br>
            <label for="autonomie">Autonomie de votre véhicule électrique (en km) :</label>
            <input type="number" id="autonomie" name="autonomie"><br>
            <input type="submit" value="Calculer">
        </form>
    </body>
    </html>
    '''

@app.route('/Introduction', methods=['POST'])
def introduction():
    message = "En France, le secteur des transports est responsable de 38 pourcent des émissions de dioxyde de carbone (CO2). Pour opérer une transition vers une mobilité plus durable, le Gouvernement s’est engagé dans le développement de la mobilité électrique. Ainsi, la loi d’orientation des mobilités fixe-t-elle comme objectif la fin de la vente de voitures particulières et de véhicules utilitaires légers neufs utilisant des énergies fossiles d’ici 2040. Depuis 2020, les immatriculations de véhicules électriques connaissent une forte progression, le nombre de ventes ayant bondi de 128 pourcent en 2020 et de 63 pourcent en 2021."
   
    evolution_nbre_voiture_elec()  #générer le grpahique 
    
    img_data = BytesIO()  #conversion du graphique en image base64
    plt.savefig(img_data, format='png')
    img_data.seek(0)
    img_base64 = base64.b64encode(img_data.read()).decode()
    
    graph_html = f'<img src="data:image/png;base64,{img_base64}" alt="Graphique d\'autonomie">'  #code HTML pour afficher le graphique
    return f'{message}<br>{graph_html}'

@app.route('/calcul', methods=['POST'])
def calcul():
    destination = request.form['destination']
    depart = request.form['depart']
    autonomie = int(request.form['autonomie'])
    
    # Ici, vous pouvez effectuer le calcul d'autonomie en fonction des données fournies

    # Par exemple, un simple exemple de calcul :
    message = f"Vous voyagez de {depart} à {destination} avec une autonomie de {autonomie} km."
    
    return message

if __name__ == '__main__':
    app.run(debug=True)