import base64
from flask import Flask, render_template, request, jsonify
import tensorflow as tf
import tensorflow_hub as hub
import numpy as np
import os
from twilio.rest import Client

app = Flask(__name__)

# Load pre-trained image embedding model (MobileNetV2)
model = hub.KerasLayer("https://tfhub.dev/google/tf2-preview/mobilenet_v2/feature_vector/4", 
                       trainable=False, input_shape=(224, 224, 3))

# Twilio Configuration
TWILIO_PHONE_NUMBER = +13204416458  # Your Twilio phone number
TO_PHONE_NUMBER = +919030942770  # The phone number to send the message to
ACCOUNT_SID = 'ACac6d1553bdcab6d877f28f2cd6e6aecf'  # Your Twilio Account SID
AUTH_TOKEN = '89dba5c81b19c2b7988bc77a1516f853'  # Your Twilio Auth Token

# Twilio Client
client = Client(ACCOUNT_SID, AUTH_TOKEN)

# Function to preprocess an image
def preprocess_image(image_data):
    img = tf.image.decode_jpeg(image_data, channels=3)
    img = tf.image.resize(img, (224, 224))  # Resize to match model input
    img = tf.keras.applications.mobilenet_v2.preprocess_input(img)
    return img

# Function to extract image embeddings from uploaded images (using raw binary data)
def extract_embeddings(image_data_list, model):
    embeddings = []
    for image_data in image_data_list:
        preprocessed_img = preprocess_image(image_data)
        embedding = model(tf.expand_dims(preprocessed_img, 0))
        embeddings.append(np.array(embedding))
    return embeddings

# Function to find the most similar image
def find_most_similar_image(uploaded_image_data, dataset_embeddings, dataset_image_paths, model):
    uploaded_image_embedding = extract_embeddings([uploaded_image_data], model)[0]

    similarities = []
    for dataset_embedding in dataset_embeddings:
        similarity = np.dot(uploaded_image_embedding.flatten(), dataset_embedding.flatten())
        similarities.append(similarity)

    most_similar_index = np.argmax(similarities)
    return dataset_image_paths[most_similar_index], similarities[most_similar_index]

# Function to convert image to base64 for embedding in HTML
def image_to_base64(image_path):
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode('utf-8')

# Function to send a message using Twilio
def send_sms(message):
    try:
        message = client.messages.create(
            body=message,
            from_=TWILIO_PHONE_NUMBER,
            to=TO_PHONE_NUMBER
        )
        print(f"Message sent: {message.sid}")
    except Exception as e:
        print(f"Error sending SMS: {str(e)}")



@app.route("/", methods=["GET", "POST"])
def upload_image():
    if request.method == "POST":
        uploaded_file = request.files["file"]
        if uploaded_file:
            uploaded_image_data = uploaded_file.read()
            dataset_image_dir = "C:\\Users\\Sailaja\\Downloads\\finaloutput\\artimages"
            dataset_image_paths = [os.path.join(dataset_image_dir, img) for img in os.listdir(dataset_image_dir) if os.path.isfile(os.path.join(dataset_image_dir, img))]
            dataset_images_data = [open(path, 'rb').read() for path in dataset_image_paths]
            dataset_embeddings = extract_embeddings(dataset_images_data, model)

            most_similar_image_path, similarity_score = find_most_similar_image(uploaded_image_data, dataset_embeddings, dataset_image_paths, model)
            similarity_score = float(similarity_score)
            print(similarity_score)
            similarity_threshold = 500  # Adjust threshold as needed
            is_below_threshold = similarity_score < similarity_threshold

            if is_below_threshold:
                # Send SMS to user when the similarity score is below threshold
                message = f"Oops! No similar image found. Similarity score: {similarity_score}"
                send_sms(message)
                
                return jsonify({
                    "message": "Oops! No similar image found.",
                    "similarity_score": similarity_score,
                    "below_threshold": is_below_threshold
                })
            else:
                similar_image_base64 = image_to_base64(most_similar_image_path)
                return jsonify({
                    "most_similar_image": f"data:image/jpeg;base64,{similar_image_base64}",
                    "similarity_score": similarity_score,
                    "below_threshold": is_below_threshold
                })

    return render_template("index.html")

if __name__ == "__main__":
    app.run(debug=True)
