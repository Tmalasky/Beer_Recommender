##### DEPENDENCIES ######
# Machine Learning toolkit
import os
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import MinMaxScaler,OneHotEncoder
from sklearn.neighbors import NearestNeighbors
import pandas as pd
import numpy as np
import tensorflow as tf

# Python SQL toolkit and Object Relational Mapper
import sqlite3


##### SCALE AND ENCODE #####

def scale_and_encode(beers_df):
    ##### SCALE NUMERICAL DATA #####

    # Scale numerical values
    scaler = MinMaxScaler()

    def scale_col_by_row(df, cols):
        # Scale values by row
        scaled_cols = pd.DataFrame(scaler.fit_transform(df[cols].T).T, columns=cols)
        df[cols] = scaled_cols
        return df

    def scale_col_by_col(df, cols):
        # Scale values by column
        scaled_cols = pd.DataFrame(scaler.fit_transform(df[cols]), columns=cols)
        df[cols] = scaled_cols
        return df

    # Scale taste profile values (across rows)
    beers_df = scale_col_by_row(beers_df, beers_df.columns[6:])

    # Scale taste profile values (across columns)
    beers_df = scale_col_by_col(beers_df, beers_df.columns[6:])

    # Scale chemical values (across columns)
    beers_df = scale_col_by_col(beers_df, beers_df.columns[3:6])


    ##### ENCODE CATEGORICAL DATA #####

    # Create OneHotEncoder instance
    enc = OneHotEncoder(sparse=False)

    # Fit the encoder and produce encoded DataFrame
    encode_df = pd.DataFrame(enc.fit_transform(beers_df['Style'].values.reshape(-1,1)))

    # Rename encoded columns
    encode_df.columns = enc.get_feature_names(['Style'])

    # Merge the two DataFrames together and drop the Style column
    encoded_styles_df = beers_df.merge(encode_df,left_index=True,right_index=True).drop("Style",1)
    return encode_df, encoded_styles_df


##### TRAINING AND TESTING SETS #####

def train_and_test(encoded_styles_df):
    # Split our preprocessed data into our features and target arrays
    # y (target) = Style
    # x (features) = ABV, Min./Max. IBU, all taste profile data
    y = encoded_styles_df[encoded_styles_df.columns[15:]].values
    X = encoded_styles_df[encoded_styles_df.columns[2:15]].values

    # Split the preprocessed data into a training and testing dataset
    X_train, X_test, y_train, y_test = train_test_split(X, y, stratify=y, random_state=78)

    return X_train, X_test, y_train, y_test


##### BUILD MODEL #####

def model(encoded_styles_df):
    X_train, X_test, y_train, y_test = train_and_test(encoded_styles_df)

    # Define the model
    number_input_features = len(X_train[0])
    hidden_nodes_layer1 = 15
    hidden_nodes_layer2 = 12
    hidden_nodes_layer3 = 8

    nn = tf.keras.models.Sequential()

    # First hidden layer
    nn.add(tf.keras.layers.Dense(units=hidden_nodes_layer1, input_dim=number_input_features, activation="relu"))

    # Second hidden layer
    nn.add(tf.keras.layers.Dense(units=hidden_nodes_layer2, activation="relu"))

    # Third hidden layer
    nn.add(tf.keras.layers.Dense(units=hidden_nodes_layer3, activation="relu"))

    # Output layer
    nn.add(tf.keras.layers.Dense(units=38, activation="softmax"))

    # Compile the model
    nn.compile(loss="categorical_crossentropy", optimizer="adam", metrics=["accuracy"])

    # Load weights
    nn.load_weights("./ML_Weight_Checkpoints/no_alcohol_model.h5")

    return nn


##### RUN MODEL ON USER DATA #####

# Predict preferred beer style based on user input
def predict_style(nn, user_input, encode_df):
    index = nn.predict(user_input).argmax()
    predicted_style = encode_df.columns[index].split('_', 1)[1]
    return predicted_style


# Function to find top 5 similar beers of same and different styles, respectively
def similar_beers(beers_df, reviews_df, user_input, style, same_style):
    if same_style:
        # Locate beers of same style
        sim_beers_df = beers_df.loc[beers_df['Style'] == style].reset_index(drop=True)
    else:
        # Locate other similar beers
        sim_beers_df = beers_df.loc[beers_df["Style"] != style].reset_index(drop=True)

    # Get numeric data for similar beers
    sim_beers_data = sim_beers_df.iloc[:, 3:]

    # Find nearest neighbors
    search = NearestNeighbors(n_neighbors=6, algorithm='ball_tree').fit(sim_beers_data)
    _, queried_indices = search.kneighbors(user_input)

    # Top 5 recommendations
    recommends_df = sim_beers_df.loc[queried_indices[0][1:]]
    recommends_df = recommends_df[['Name', 'Brewery', 'Style']]
    recommends_df = pd.merge(recommends_df, reviews_df, how='inner', on=['Name', 'Brewery', 'Style'])
    recommends_df = recommends_df.sort_values(by=['review_overall'], ascending=False)
    recommends_df.reset_index(drop=True, inplace=True)
    recommends_df.columns = ['Name', 'Brewery', 'Style', 'ABV', 'Overall (1-5)', 'Aroma', 'Appearance', 'Palate', 'Taste', 'Number of Reviews']
    
    # Reset the index
    recommends_df.set_index('Name', drop=True, inplace=True)
    recommends_df = recommends_df.rename_axis(None, axis='index')
    recommends_df.index.rename('Beer', inplace=True)

    # Occasional issue with ABV rounding, map to ensure it is correct
    # before returning results.
    recommends_df['ABV'] = recommends_df['ABV'].map("{:.1f}".format)

    return recommends_df


##### DRIVER FUNCTION #####

def find_beers(user_input):
    
    ##### IMPORT DATA #####

    # Connect to the database
    con = sqlite3.connect("./beer_data.sqlite")

    # Create Pandas DataFrames
    beers_df = pd.read_sql_query("SELECT * FROM taste_profiles", con)
    reviews_df = pd.read_sql_query("SELECT * FROM reviews", con)


    ##### FORMAT DATAFRAMES #####

    # Round review scores to 2 decimal places
    for col in reviews_df.columns[4:9]:
        reviews_df[col] = reviews_df[col].map("{:.2f}".format)

    # Close database connection
    con.close()

    
    ##### BUILD MODEL #####

    # Scale and Encode data
    encode_df, encoded_styles_df = scale_and_encode(beers_df)

    nn = model(encoded_styles_df)


    ##### FORMAT USER DATA #####

    # Convert data to percentages
    user_input = np.asarray(user_input).astype(np.float64)
    user_input = user_input / 100

    # Add random ABV to array
    user_input = np.insert(user_input, 0, encoded_styles_df.sample().iloc[0][2])

    # Determine Min./Max. IBU by adding/subtracting
    # the average std. deviation of the IBU and Bitter
    # columns from the user's bitterness score
    user_input = np.insert(user_input, 1, user_input[2] - 0.2)
    user_input = np.insert(user_input, 2, user_input[2] + 0.2)
    user_input = user_input.reshape(1,-1)

    ##### PERFORM CALCULATIONS #####
    
    # Predict preferred style
    pred_style = predict_style(nn, user_input, encode_df)

    # Top 5 similar beers of same style (by overall review score)
    top_5_same_style = similar_beers(beers_df, reviews_df, user_input, pred_style, same_style=True).to_html(justify='center', classes='table')
    
    # Top 5 similar beers of other styles (by overall review score)
    top_5_diff_style = similar_beers(beers_df, reviews_df, user_input, pred_style, same_style=False).to_html(justify='center', classes='table')

    

    return pred_style, top_5_same_style, top_5_diff_style
