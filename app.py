import streamlit as st
import pandas as pd
from datetime import datetime
import requests ,json ,time , sqlite3 , os , re
from bs4 import BeautifulSoup 
from io import BytesIO


# ---------------- CONFIG ----------------
st.set_page_config(page_title="Car Listings App", layout="wide")
DB_FILE = os.path.join(os.path.dirname(__file__), "cars.db")


# ---------------- DATABASE ----------------
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS autotrader (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            price TEXT,
            location TEXT,
            odometer TEXT,
            image_src TEXT,
            ad_link TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS kjiji (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT,
            name TEXT,
            description TEXT,
            image TEXT,
            price TEXT,
            priceCurrency TEXT,
            url TEXT UNIQUE,
            brand_name TEXT,
            mileage_value TEXT,
            mileage_unitCode TEXT,
            model TEXT,
            vehicleModelDate TEXT,
            bodyType TEXT,
            color TEXT,
            numberOfDoors TEXT,
            fuelType TEXT,
            vehicleTransmission TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()

def insert_car_autotreader(title, price, location, odometer, image_src,ad_link):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute("""
        INSERT INTO autotrader (title, price, location, odometer, image_src, ad_link, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (title, price, location, odometer, image_src, ad_link,now))
    conn.commit()
    conn.close()

def insert_car_kijiji(car):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    c.execute("""
        INSERT OR IGNORE INTO kjiji (
            type, name, description, image, price, priceCurrency, url,
            brand_name, mileage_value, mileage_unitCode, model,
            vehicleModelDate, bodyType, color, numberOfDoors,
            fuelType, vehicleTransmission, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        car.get("@type"),
        car.get("name"),
        car.get("description"),
        car.get("image"),
        car.get("price"),
        car.get("priceCurrency"),
        car.get("url"),
        car.get("brand.name"),
        car.get("mileageFromOdometer.value"),
        car.get("mileageFromOdometer.unitCode"),
        car.get("model"),
        car.get("vehicleModelDate"),
        car.get("bodyType"),
        car.get("color"),
        car.get("numberOfDoors"),
        car.get("vehicleEngine.fuelType"),
        car.get("vehicleTransmission"),
        now
    ))


    conn.commit()
    conn.close()

def get_all_autotrader_cars():
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT * FROM autotrader ORDER BY id DESC", conn)
    conn.close()
    return df

def get_all_kijiji_cars():
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT * FROM kjiji ORDER BY id DESC", conn)
    conn.close()
    return df


def merge_car_data():
    kdf = get_all_kijiji_cars()
    adf = get_all_autotrader_cars()

    # Add a source column
    kdf["source"] = "Kijiji"
    adf["source"] = "Autotrader"

    # --- Kijiji normalization ---
    kdf = kdf.rename(columns={
        "name": "title",
        "priceCurrency": "currency",
        "brand_name": "brand",
        "mileage_value": "odometer",
        "url": "ad_link",
        "image": "image_src"
    })[[
        "source", "title", "price", "currency", "brand",
        "model", "vehicleModelDate", "bodyType", "color",
        "fuelType", "vehicleTransmission", "odometer",
        "image_src", "ad_link", "created_at"
    ]]

    # --- Autotrader normalization ---
    # Add missing columns if not present
    for col in ["title", "price", "odometer", "image_src", "ad_link", "created_at"]:
        if col not in adf.columns:
            adf[col] = None

    # Add optional fields missing from Autotrader
    for col in ["currency", "brand", "model", "vehicleModelDate", "bodyType", "color", "fuelType", "vehicleTransmission"]:
        adf[col] = None

    adf = adf[[
        "source", "title", "price", "currency", "brand",
        "model", "vehicleModelDate", "bodyType", "color",
        "fuelType", "vehicleTransmission", "odometer",
        "image_src", "ad_link", "created_at"
    ]]

    # Merge both
    merged = pd.concat([kdf, adf], ignore_index=True)
    merged.sort_values(by="created_at", ascending=False, inplace=True)
    return merged
    

def to_excel_bytes(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Merged Cars')
    return output.getvalue()
# Initialize the database
init_db()

# ---------------- SIDEBAR ----------------
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", ["📊 View Cars", "📝 Add Car"])

# ---------------- PAGE 1: VIEW ----------------
if page == "📊 View Cars":
    tokenTitle = st.text_input("Add your token", "enterprise-api.kdp.kardataservices")
    st.title("🚗 Autotrader Car Listings")
    with st.expander("See Autotrader explanation"):
        df = get_all_autotrader_cars()

        if df.empty:
            st.info("No cars found. Add new cars using the 'Add Car' page.")
        else:
            # Show DataFrame
            st.dataframe(df, use_container_width=True)

            # Card-style display
            for _, row in df.iterrows():
                with st.container():
                    cols = st.columns([1, 3])
                    with cols[0]:
                        if row['image_src']:
                            st.image(row['image_src'], width=180)
                    with cols[1]:
                        st.subheader(row['title'])
                        
                        

                        brands = ['AM General','Acura','Alfa Romeo','American Motors (AMC)','Aston Martin','Audi','BMW','Bentley','BrightDrop','Buick','Cadillac','Chevrolet','Chrysler','Daewoo','Datsun','Dodge','Ducati','Eagle','FIAT','Ferrari','Fiat','Fisker','Ford','Freightliner','GMC','Genesis','Geo','HUMMER','Harley-Davidson','Hino','Honda','Hyundai','INEOS','INFINITI','Indian','International','Isuzu','Jaguar','Jeep','KTM','Karma','Kawasaki','Kenworth','Kia','Lamborghini','Land Rover','Lexus','Lincoln','Lordstown','Lotus','Lucid','MINI','MV-1','Mack','Maserati','Maybach','Mazda','McLaren','Mercedes-Benz','Mercury','Merkur','Mitsubishi','Moto Guzzi','Nissan','Oldsmobile','Panoz','Peterbilt','Peugeot','Plymouth','Polestar','Pontiac','Porsche','Ram','Renault','Rivian','Rolls-Royce','Saab','Saturn','Scion','Smart','Sterling','Subaru','Suzuki','Tesla','Toyota','Triumph','VPG','Victory','VinFast','Volkswagen','Volvo','Western Star','Yamaha','Yugo','Zero','smart']
                        matches = [brand for brand in brands if brand.lower() in row['title'].lower()]
                        if tokenTitle:
                            match = re.search(r'Authorization:\s*Bearer\s+([A-Za-z0-9\-\._]+)', tokenTitle)
                            if match:
                                token = match.group(1)
                                print("====================")
                                print(token)
                                
                                if st.button(f"{row['id']} - get market guide - {row['title'].lower()}"):
                                    
                                
                                    headers = {
                                        'Host': 'enterprise-api.kdp.kardataservices.com',
                                        'Sec-Ch-Ua-Platform': '"Windows"',
                                        'Authorization': f'Bearer {token}',
                                        'Accept-Language': 'en-US,en;q=0.9',
                                        'Sec-Ch-Ua': '"Chromium";v="141", "Not?A_Brand";v="8"',
                                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36',
                                        'Sec-Ch-Ua-Mobile': '?0',
                                        'Accept': '*/*',
                                        'Origin': 'https://app.openlane.ca',
                                        'Sec-Fetch-Site': 'cross-site',
                                        'Sec-Fetch-Mode': 'cors',
                                        'Sec-Fetch-Dest': 'empty',
                                        'Referer': 'https://app.openlane.ca/',
                                        # 'Accept-Encoding': 'gzip, deflate, br',
                                        'Priority': 'u=1, i',
                                    }

                                    params = {
                                        'yearMin': '1940',
                                        'yearMax': '2027',
                                        'makeNames': f'{str(matches[0])}',
                                    }

                                    marketresponse = requests.get(
                                        'https://enterprise-api.kdp.kardataservices.com/vehicle-retail-data/marketguide/models',
                                        params=params,
                                        headers=headers,
                                        verify=False,
                                    )


                                    mdata = json.loads(marketresponse.text)['modelNames']
                                    model = [brand for brand in mdata if brand.lower() in row['title'].lower()][0]

                                    years = re.findall(r'\b(?:19|20)\d{2}\b', row['title'].lower())
                                    if years:
                                        year = str(int(years[0])-1)
                                        
                                        odometerMax = re.search(r'[\d,]+', row['odometer'])
                                        if odometerMax:
                                            num_int = int(odometerMax.group(0).replace(',', '')) + 5000
                                        params = {
                                            'teamId': 'ompProd',
                                            'makeNames': f'{str(matches[0])}',
                                            'modelNames': f'{str(model)}',
                                            'yearMin': f'{year}',
                                            'yearMax': '2027',
                                            'odometerMin': '0',
                                            'odometerMax': f'{str(num_int)}',
                                            'saleDateFrom': '2025-08-02',
                                            'saleDateTo': '2025-10-31',
                                            'sortBy': 'sale_date',
                                            'sortOrder': 'desc',
                                            'page': '0',
                                            'size': '10',
                                            'countryCode': 'CA',
                                            'organizationId': 'a10514a4-a594-4736-bcc8-3978ec88145a',
                                        }

                                        finalresponse = requests.get(
                                            'https://enterprise-api.kdp.kardataservices.com/vehicle-retail-data/marketguide',
                                            params=params,
                                            headers=headers,
                                            verify=False,
                                        )
                                        data = json.loads(finalresponse.text)
                                        del data['marketGuideVehicles']
                                        st.write(data)
                            else:
                                st.write(f"no token !!!")
                            
                        else:
                            st.write(f"no token !!!")




                        st.write(f"**Price:** {row['price']}")
                        st.write(f"**Location:** {row['location']}")
                        st.write(f"**Odometer:** {row['odometer']}")
                        st.caption(f"🕒 Added on: {row['created_at']}")
                        st.markdown(f"[🔗 View Ad]({row['ad_link']})", unsafe_allow_html=True)
                    st.divider()

            # Download CSV

            excel_data = to_excel_bytes(df)
            st.download_button(
                label="📊 Download autotreader Excel",
                data=excel_data,
                file_name="autotreader.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )


            csv = df.to_csv(index=False).encode("utf-8")
            st.download_button(
                "📥 Download CSV",
                data=csv,
                file_name="cars.csv",
                mime="text/csv",
            )
    with st.expander("See Kijiji Vehicles"):
        kdf = get_all_kijiji_cars()

        if kdf.empty:
            st.info("🚗 No Kijiji cars found. Add new cars or scrape data first.")
        else:
            # Display DataFrame overview
            st.dataframe(kdf, use_container_width=True)

            # Card-style view
            for _, row in kdf.iterrows():
                with st.container():
                    cols = st.columns([1, 3])

                    # Left column — image
                    with cols[0]:
                        if row["image"]:
                            st.image(row["image"], width=180)
                        else:
                            st.image("https://via.placeholder.com/180x120?text=No+Image", width=180)

                    # Right column — vehicle details
                    with cols[1]:
                        st.subheader(row["name"] or "Unknown Vehicle")



                        brands = ['AM General','Acura','Alfa Romeo','American Motors (AMC)','Aston Martin','Audi','BMW','Bentley','BrightDrop','Buick','Cadillac','Chevrolet','Chrysler','Daewoo','Datsun','Dodge','Ducati','Eagle','FIAT','Ferrari','Fiat','Fisker','Ford','Freightliner','GMC','Genesis','Geo','HUMMER','Harley-Davidson','Hino','Honda','Hyundai','INEOS','INFINITI','Indian','International','Isuzu','Jaguar','Jeep','KTM','Karma','Kawasaki','Kenworth','Kia','Lamborghini','Land Rover','Lexus','Lincoln','Lordstown','Lotus','Lucid','MINI','MV-1','Mack','Maserati','Maybach','Mazda','McLaren','Mercedes-Benz','Mercury','Merkur','Mitsubishi','Moto Guzzi','Nissan','Oldsmobile','Panoz','Peterbilt','Peugeot','Plymouth','Polestar','Pontiac','Porsche','Ram','Renault','Rivian','Rolls-Royce','Saab','Saturn','Scion','Smart','Sterling','Subaru','Suzuki','Tesla','Toyota','Triumph','VPG','Victory','VinFast','Volkswagen','Volvo','Western Star','Yamaha','Yugo','Zero','smart']
                        matches = [brand for brand in brands if brand.lower() in row['name'].lower()]
                        if tokenTitle:
                            match = re.search(r'Authorization:\s*Bearer\s+([A-Za-z0-9\-\._]+)', tokenTitle)
                            if match:
                                token = match.group(1)
                                print("====================")
                                print(token)
                                
                                if st.button(f"{row['id']} - get market guide - {row['name'].lower()}"):
                                    
                                
                                    headers = {
                                        'Host': 'enterprise-api.kdp.kardataservices.com',
                                        'Sec-Ch-Ua-Platform': '"Windows"',
                                        'Authorization': f'Bearer {token}',
                                        'Accept-Language': 'en-US,en;q=0.9',
                                        'Sec-Ch-Ua': '"Chromium";v="141", "Not?A_Brand";v="8"',
                                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36',
                                        'Sec-Ch-Ua-Mobile': '?0',
                                        'Accept': '*/*',
                                        'Origin': 'https://app.openlane.ca',
                                        'Sec-Fetch-Site': 'cross-site',
                                        'Sec-Fetch-Mode': 'cors',
                                        'Sec-Fetch-Dest': 'empty',
                                        'Referer': 'https://app.openlane.ca/',
                                        # 'Accept-Encoding': 'gzip, deflate, br',
                                        'Priority': 'u=1, i',
                                    }

                                    params = {
                                        'yearMin': '1940',
                                        'yearMax': '2027',
                                        'makeNames': f'{str(matches[0])}',
                                    }

                                    marketresponse = requests.get(
                                        'https://enterprise-api.kdp.kardataservices.com/vehicle-retail-data/marketguide/models',
                                        params=params,
                                        headers=headers,
                                        verify=False,
                                    )


                                    mdata = json.loads(marketresponse.text)['modelNames']
                                    
                                    model = [brand for brand in mdata if brand.lower() in row['name'].lower()]
                                    if model:

                                        years = re.findall(r'\b(?:19|20)\d{2}\b', row['name'].lower())
                                        if years:
                                            year = str(int(years[0])-1)
                                            
                                            odometerMax = re.search(r'[\d,]+', row['mileage_value'])
                                            if odometerMax:
                                                num_int = int(odometerMax.group(0).replace(',', '')) + 5000
                                            params = {
                                                'teamId': 'ompProd',
                                                'makeNames': f'{str(matches[0])}',
                                                'modelNames': f'{str(model[0])}',
                                                'yearMin': f'{year}',
                                                'yearMax': '2027',
                                                'odometerMin': '0',
                                                'odometerMax': f'{str(num_int)}',
                                                'saleDateFrom': '2025-08-02',
                                                'saleDateTo': '2025-10-31',
                                                'sortBy': 'sale_date',
                                                'sortOrder': 'desc',
                                                'page': '0',
                                                'size': '10',
                                                'countryCode': 'CA',
                                                'organizationId': 'a10514a4-a594-4736-bcc8-3978ec88145a',
                                            }

                                            finalresponse = requests.get(
                                                'https://enterprise-api.kdp.kardataservices.com/vehicle-retail-data/marketguide',
                                                params=params,
                                                headers=headers,
                                                verify=False,
                                            )
                                            data = json.loads(finalresponse.text)
                                            del data['marketGuideVehicles']
                                            st.write(data)
                                        else:
                                            st.warning(f"no year matched !!!")
                                    else:
                                            st.warning(f"no model matched !!!")
                                
                                
                            else:
                                st.write(f"no token !!!")






                        st.write(f"**Type:** {row['type'] or 'N/A'}")
                        st.write(f"**Model:** {row['model'] or 'N/A'} ({row['vehicleModelDate'] or 'N/A'})")
                        st.write(f"**Price:** {row['price'] or 'N/A'} {row['priceCurrency'] or ''}")
                        st.write(f"**Brand:** {row['brand_name'] or 'N/A'}")
                        st.write(f"**Body Type:** {row['bodyType'] or 'N/A'}")
                        st.write(f"**Color:** {row['color'] or 'N/A'}")
                        st.write(f"**Fuel Type:** {row['fuelType'] or 'N/A'}")
                        st.write(f"**Transmission:** {row['vehicleTransmission'] or 'N/A'}")

                        st.markdown("---")
                        
                        st.write(f"**Mileage:** {row['mileage_value'] or 'N/A'} {row['mileage_unitCode'] or ''}")
                        st.write(f"**Doors:** {row['numberOfDoors'] or 'N/A'}")
                        st.caption(f"🕒 Added on: {row['created_at']}")

                        if row["url"]:
                            st.markdown(f"[🔗 View Ad]({row['url']})", unsafe_allow_html=True)

                    st.divider()

            # --- Download button ---
            excel_data = to_excel_bytes(kdf)
            st.download_button(
                label="📊 Download kjiji Excel",
                data=excel_data,
                file_name="kijiji_cars.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

            csv = kdf.to_csv(index=False).encode("utf-8")
            st.download_button(
                "📥 Download All Cars (CSV)",
                data=csv,
                file_name="kijiji_cars.csv",
                mime="text/csv",
            )       
    with st.expander("🧩 Combined View: Kijiji + Autotrader"):
        merged_df = merge_car_data()

        if merged_df.empty:
            st.info("No cars found in either table.")
        else:
            st.dataframe(merged_df, use_container_width=True)

            # Card-style display
            for _, row in merged_df.iterrows():
                with st.container():
                    cols = st.columns([1, 3])
                    with cols[0]:
                        if row["image_src"]:
                            st.image(row["image_src"], width=180)
                        else:
                            st.image("https://via.placeholder.com/180x120?text=No+Image", width=180)
                    with cols[1]:
                        st.subheader(row["title"] or "Unknown Vehicle")
                        st.caption(f"📦 Source: {row['source']}")
                        st.write(f"**Price:** {row['price'] or 'N/A'} {row['currency'] or ''}")
                        st.write(f"**Brand:** {row['brand'] or 'N/A'}")
                        st.write(f"**Model:** {row['model'] or 'N/A'} ({row['vehicleModelDate'] or 'N/A'})")
                        st.write(f"**Body Type:** {row['bodyType'] or 'N/A'}")
                        st.write(f"**Color:** {row['color'] or 'N/A'}")
                        st.write(f"**Fuel Type:** {row['fuelType'] or 'N/A'}")
                        st.write(f"**Transmission:** {row['vehicleTransmission'] or 'N/A'}")
                        st.write(f"**Odometer:** {row['odometer'] or 'N/A'}")
                        st.caption(f"🕒 Added on: {row['created_at']}")
                        if row["ad_link"]:
                            st.markdown(f"[🔗 View Ad]({row['ad_link']})", unsafe_allow_html=True)
                    st.divider()

            # Excel Download
            excel_data = to_excel_bytes(merged_df)
            st.download_button(
                label="📊 Download Combined Excel",
                data=excel_data,
                file_name="merged_cars.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
# ---------------- PAGE 2: ADD ----------------
elif page == "📝 Add Car":
    st.title("📝 Add New Car Listing")

    AutotraderSubmitted = st.button("Updata Autotrader Car")
    KjijiSubmitted = st.button("Updata Kjiji Car")
    
    if KjijiSubmitted:

        cookies = {
            'kjses': 'a3ada55c-3dda-4d3b-a2f1-5a2dc3e6d11e^MSym5/LO9nctRVl8JS0kFA==',
            'machId': '22fb321cba3b00c1b9e5ec088612772657052a66147091639177d4bb1d9b30c7619ed61ccc0c45ded10273971642021362cab9ba47cc83305e4d338bf26682f3',
            'up': '%7B%22ln%22%3A%22725948023%22%2C%22ls%22%3A%22sv%3DLIST%26sf%3DdateDesc%22%7D',
        }

        headers = {
            'Host': 'www.kijiji.ca',
            'Cache-Control': 'max-age=0',
            'Sec-Ch-Ua': '"Chromium";v="139", "Not;A=Brand";v="99"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"Windows"',
            'Accept-Language': 'en-US,en;q=0.9',
            'Upgrade-Insecure-Requests': '1',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-User': '?1',
            'Sec-Fetch-Dest': 'document',
            # 'Accept-Encoding': 'gzip, deflate, br',
            'Priority': 'u=0, i',
            # 'Cookie': 'kjses=a3ada55c-3dda-4d3b-a2f1-5a2dc3e6d11e^MSym5/LO9nctRVl8JS0kFA==; machId=22fb321cba3b00c1b9e5ec088612772657052a66147091639177d4bb1d9b30c7619ed61ccc0c45ded10273971642021362cab9ba47cc83305e4d338bf26682f3; up=%7B%22ln%22%3A%22725948023%22%2C%22ls%22%3A%22sv%3DLIST%26sf%3DdateDesc%22%7D',
        }

        params = {
            'view': 'list',
        }
        flagKjiji = False
        kresponse = requests.get(
            'https://www.kijiji.ca/b-cars-trucks/ontario/c174l9004',
            params=params,
            cookies=cookies,
            headers=headers,
            verify=False,
        )
        if kresponse.status_code != 200:
            st.warning("⚠️ Attempt failed. Retrying in 30 seconds...")

            time.sleep(30)
            for attempt in range(3):
                kresponse = requests.get(
                    'https://www.kijiji.ca/b-cars-trucks/ontario/c174l9004',
                    params=params,
                    cookies=cookies,
                    headers=headers,
                    verify=False,
                )
                if kresponse.status_code == 200:
                    st.success("✅ Done! Kijiji Cars successfully connected in the api.")
                    flagKjiji = True
                    break
                st.warning(f"⚠️ Attempt failed {attempt + 1}. Retrying in 60 seconds...")
                
                time.sleep(60)
        else:
            flagKjiji = True
            st.success("✅ Done! Kijiji Cars successfully connected in the api.")
        
        if flagKjiji == True:
           
            html = kresponse.text

            # Parse HTML
            soup = BeautifulSoup(html, "html.parser")

            # Find all <script type="application/ld+json"> blocks
            json_blocks = []
            for script in soup.find_all("script", type="application/ld+json"):
                try:
                    data = json.loads(script.string)  # Convert JSON string → Python dict/list
                    json_blocks.append(data)
                except json.JSONDecodeError as e:
                    print("Skipping invalid JSON block:", e)

            # Now json_blocks is a Python list of JSON objects
            

            def extract_vehicle_info(vehicle_data):
                item = vehicle_data.get("item", {})
                offers = item.get("offers", {})
                brand = item.get("brand", {})
                mileage = item.get("mileageFromOdometer", {})
                engine = item.get("vehicleEngine", {})

                return {
                    "@type": item.get("@type"),
                    "name": item.get("name"),
                    "description": item.get("description"),
                    "image": item.get("image"),
                    "price": offers.get("price"),
                    "priceCurrency": offers.get("priceCurrency"),
                    "url": item.get("url"),
                    "brand.name": brand.get("name"),
                    "mileageFromOdometer.value": mileage.get("value"),
                    "mileageFromOdometer.unitCode": mileage.get("unitCode"),
                    "model": item.get("model"),
                    "vehicleModelDate": item.get("vehicleModelDate"),
                    "bodyType": item.get("bodyType"),
                    "color": item.get("color"),
                    "numberOfDoors": item.get("numberOfDoors"),
                    "vehicleEngine.fuelType": engine.get("fuelType"),
                    "vehicleTransmission": item.get("vehicleTransmission")
                }

            vehicles = [extract_vehicle_info(v) for v in json_blocks[0]['itemListElement']]
            for v in vehicles:
                insert_car_kijiji(v)

            st.success("✅ Done! Kjiji Cars successfully added to the database.")




    if AutotraderSubmitted:
        cookies = {
    'atOptUser': '07c737ae-676c-40f6-96c6-fea0904dc57d',
    'as24Visitor': '130721fe-45dd-4393-91d3-1d5cca3e11ef',
    'searchBreadcrumbs': '%7B%22srpBreadcrumb%22%3A%5B%7B%22Text%22%3A%22Cars%2C%20Trucks%20%26%20SUVs%22%2C%22Url%22%3A%22%2Fcars%2F%3Frcp%3D25%26rcs%3D0%26srt%3D9%26prx%3D-1%26hprc%3DTrue%26wcp%3DTrue%26adtype%3DPrivate%22%7D%2C%7B%22Text%22%3A%22Ontario%22%2C%22Url%22%3A%22%2Fcars%2Fon%2F%3Frcp%3D25%26rcs%3D0%26srt%3D9%26prx%3D-2%26prv%3DOntario%26loc%3Dn6b3r1%26hprc%3DTrue%26wcp%3DTrue%26adtype%3DPrivate%22%7D%2C%7B%22Text%22%3A%22London%22%2C%22Url%22%3A%22%2Fcars%2Fon%2Flondon%2F%3Frcp%3D50%26rcs%3D0%26srt%3D9%26prx%3D1000%26prv%3DOntario%26loc%3Dn6b3r1%26hprc%3DTrue%26wcp%3DTrue%26adtype%3DPrivate%22%7D%5D%2C%22isFromSRP%22%3Afalse%2C%22neighbouringIds%22%3Anull%7D',
    'visid_incap_820541': 'fmQpcehBR4mc6IUbvRUGPMhTA2kAAAAAQUIPAAAAAAA2yEGxXGFkjXQmhak2yB2H',
    'nlbi_820541_1646237': 'MEDNGOwUTQuiKeecpRL4bAAAAACM8JeUVOw3B8bAoAPaCfjQ',
    'incap_ses_475_820541': 'D1ngB77s0nIpba4ocIqXBslTA2kAAAAAEe6Z3X521K8cBj3lvIrmrw==',
    'optimizelyEndUserId': 'oeu1761825745421r0.4037649605335607',
    'cbnr': '1',
    'optimizelySession': '1761825751335',
    '_gcl_au': '1.1.2029418894.1761825757',
    'at_as24_site_exp': 'at',
    'nlbi_820541_3122371': 'vt8ifvlMf395FI5JpRL4bAAAAAB1OULur5TUXYw+htmy17mF',
    '__GTMADBLOCKER__': 'no',
    'pCode': 'N6B3R1',
    'srchLocation': '%7B%22Location%22%3A%7B%22Address%22%3Anull%2C%22City%22%3A%22London%22%2C%22Latitude%22%3A42.97735595703125%2C%22Longitude%22%3A-81.24272918701172%2C%22Province%22%3A%22ON%22%2C%22PostalCode%22%3A%22N6B%203R1%22%2C%22Type%22%3A%22%22%7D%2C%22UnparsedAddress%22%3A%22n6b3r1%22%7D',
    '{E7ABF06F-D6A6-4c25-9558-3932D3B8A04D}': '',
    'lastsrpurl': '/cars/on/london/?rcp=50&rcs={}&srt=9&prx=1000&prv=Ontario&loc=n6b3r1&hprc=True&wcp=True&adtype=Private&inMarket=advancedSearch',
    'PageSize': '50',
    'SortOrder': 'CreatedDateDesc',
    '_switch_session_id': 'c04b8b72-a7d9-4d92-8562-8011a349f0df',
    '_rdt_uuid': '1761825766275.249ef6bd-1e8a-49b2-bfa6-4d4b449fcb5f',
    'ci_uid': '1c04ac02-3707-4e74-8f2d-9ee6ca34b0b0',
    '_cc_id': '5fc3c25bd8643375c9ac9dda701a58db',
    'panoramaId': 'e64469f18895889a88b48791f937185ca02c2d16ce1c7df0f548498579f7dd96',
    '_ga': 'GA1.1.161662328.1761825771',
    '_ga_PHSPDB57ZK': 'GS2.1.s1761825771$o1$g1$t1761825771$j60$l0$h520580996',
    '_uetsid': '5cfa8170b58811f099452b3056482c66',
    '_uetvid': '5cfb0100b58811f082f2eb6a115d961c',
    'FPID': 'FPID2.2.2DDrR4YiRyrMKqC17qzshJIbe7wk162DtP8QXAjF0Gk%3D.1761825771',
    'FPAU': '1.1.2029418894.1761825757',
    'FPLC': 'In0ZYC6OrYrUVKn%2BxWA0VTcCFoSeGW4pBVM1JKKph0%2Fx6ZDg84Awr8wdGZGwmzN8lrdS1AI7kbnw8n%2FSNHuWrhN7JH3fw42ioGMRwLsHgidau0sfeXB1rN6NX32mFA%3D%3D',
    '_fbp': 'fb.1.1761825774555.1206315652',
    '_switch_session': 'eyJjbGlja2lkcyI6e30sImNvb2tpZXMiOnsicmR0X3V1aWQiOiIxNzYxODI1NzY2Mjc1LjI0OWVmNmJkLTFlOGEtNDliMi1iZmE2LTRkNGI0NDlmY2I1ZiIsImdhIjoiR0ExLjEuMTYxNjYyMzI4LjE3NjE4MjU3NzEiLCJmYnAiOiJmYi4xLjE3NjE4MjU3NzQ1NTUuMTIwNjMxNTY1MiJ9LCJpcEFkZHJlc3MiOiIxOTYuMTMxLjI1NS4zNyIsInVzZXJBZ2VudCI6Ik1vemlsbGEvNS4wIChXaW5kb3dzIE5UIDEwLjA7IFdpbjY0OyB4NjQpIEFwcGxlV2ViS2l0LzUzNy4zNiAoS0hUTUwsIGxpa2UgR2Vja28pIENocm9tZS8xMzkuMC4wLjAgU2FmYXJpLzUzNy4zNiIsImVtIjpbXSwicGgiOltdLCJzaWQiOiJjMDRiOGI3Mi1hN2Q5LTRkOTItODU2Mi04MDExYTM0OWYwZGYiLCJzdGFydF90aW1lIjoxNzYxODI1NzYyODE4LCJhY2NvdW50X2lkIjoiazhuYW9tdUZyZzA4aWdaMyIsInVybCI6Imh0dHBzOi8vd3d3LmF1dG90cmFkZXIuY2EvY2Fycy9vbi9sb25kb24vP3JjcD01MCZyY3M9e30mc3J0PTkmcHJ4PTEwMDAmcHJ2PU9udGFyaW8mbG9jPW42YjNyMSZocHJjPVRydWUmd2NwPVRydWUmYWR0eXBlPVByaXZhdGUmaW5NYXJrZXQ9YWR2YW5jZWRTZWFyY2gifQ==',
    '_ga_RMZMLXC8S1': 'GS2.1.s1761825775$o1$g0$t1761825775$j60$l0$h0',
    'sa-user-id': 's%253A0-a5f9c688-6af2-597c-7a50-6ac21ea78c15.oPMX3gBxrQ3KEhs4lVkEXTKan24hYMufc8rb2OK7TWo',
    'sa-user-id-v2': 's%253ApfnGiGryWXx6UGrCHqeMFcSD_yU.p4CjvqHIcwdpU3B5FXXIWxDfPSMf1elKblDyjBSEgII',
    'sa-user-id-v3': 's%253AAQAKIP0Xy0c_9ZFajRI89pA9Zps06LE952BO6gBlBWZKWjApEAEYAyDwp43IBjABOgTIcrGlQgTck8g-.XxJ1WOOjRyqsMvlfFwc2DXZ9%252Fn1tfUuFKd8zeV15gOA',
    'tgcid': '161662328.1761825771',
    'panoramaId_expiry': '1762430577631',
    'panoramaIdType': 'panoDevice',
    'cc_audpid': '5fc3c25bd8643375c9ac9dda701a58db',
    '_scor_uid': 'b81be454d6d144979ea4cd0af7fe7185',
    '_clck': 'b6qezn%5E2%5Eg0l%5E0%5E2129',
    '_tt_enable_cookie': '1',
    '_ttp': '01K8TFZWA74293RG043WN8QZVH_.tt.1',
    '__qca': 'P1-51907248-63d9-487d-a7da-d35082f53b6d',
    '_td': '568ab9ea-4918-4923-a88a-88a99a4feca6',
    '_pin_unauth': 'dWlkPVlUZzVOMk5sWm1RdE1XUTJOQzAwWkRjeUxXRmtaVEF0WVRSak16Um1NV1F3Tnpoaw',
    'FCCDCF': '%5Bnull%2Cnull%2Cnull%2Cnull%2Cnull%2Cnull%2C%5B%5B32%2C%22%5B%5C%225e9f1905-80e2-414a-b119-56a12b5e5111%5C%22%2C%5B1761825779%2C74000000%5D%5D%22%5D%5D%5D',
    '__T2CID__': 'b6272444-9f25-4552-8030-201ff15e8bc1',
    'FCNEC': '%5B%5B%22AKsRol_na-AQ6_R8pdXUdUL18Dftq3r-DQnYI0i-q-tixcAMRWsCiq7TLYFedKGp5ZDhL41Bo5_-X6rqXHazLA52R81Vx7A0x-cyefbHWzmHyjTx-GEmyIMO4IbBlexLzz0mnFaqenFgV43IyhVMxeepa36cItNNHg%3D%3D%22%5D%5D',
    'cto_bundle': 'ixD78l9HMzV6MlJnYSUyQkpCUGVBM3REJTJCc0REOWFiQVBRT2daeGQlMkZpZ0VERjElMkJXSWRDJTJGbUtPMyUyQllDRU5OVXlSYTZTYkFKaVJvdURzekxRNTRHSEV0R1clMkJhSSUyQmJFbTlWUzlPOUc3YkFUV29tN1plOXZsWU95enJ1V0UzRm1VZWVjMUZQSUtiWmNiNVo3SmsySWJRdGpkWlpFV3dMblRNSHkwYkltVVBldUlYRiUyQjlIcGMlM0Q',
    '_clsk': '1q07egb%5E1761826572802%5E2%5E1%5El.clarity.ms%2Fcollect',
    '_ga_PCMZZ2EWK8': 'GS2.1.s1761825776$o1$g1$t1761826574$j60$l0$h0',
    'ttcsid': '1761825780107::Cotp8QHVqvwLanwIJaWl.1.1761826591926.0',
    'ttcsid_C7TFG3E0MJON0LQMRBS0': '1761825780093::e7nW3pAuDE1nClseStGA.1.1761826591926.0',
    'searchState': '{"isUniqueSearch":false,"make":null,"model":null}',
        }

        headers = {
            'Host': 'www.autotrader.ca',
            # 'Content-Length': '1772',
            'X-Newrelic-Id': 'UgUPVV5SGwIAVVlRAQIGX1Q=',
            'Ms': '1',
            'Sec-Ch-Ua-Platform': '"Windows"',
            'Accept-Language': 'en-US,en;q=0.9',
            'Sec-Ch-Ua': '"Chromium";v="139", "Not;A=Brand";v="99"',
            'Newrelic': 'eyJ2IjpbMCwxXSwiZCI6eyJ0eSI6IkJyb3dzZXIiLCJhYyI6IjYzODQ4MSIsImFwIjoiMTEwMzI5MDIzOSIsImlkIjoiNzA1NmU3MDNlM2VlYmM4MSIsInRyIjoiZmFiMTU2ZGUxMGE0NDFkNzAzNDQ1MWYxMzVjYmVmYTUiLCJ0aSI6MTc2MTgyNjU5MTk1N319',
            'Allowmvt': 'true',
            'Sec-Ch-Ua-Mobile': '?0',
            'Traceparent': '00-fab156de10a441d7034451f135cbefa5-7056e703e3eebc81-01',
            'X-Requested-With': 'XMLHttpRequest',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Content-Type': 'application/json',
            'Tracestate': '638481@nr=0-1-638481-1103290239-7056e703e3eebc81----1761826591957',
            'Isajax': 'true',
            'Origin': 'https://www.autotrader.ca',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Dest': 'empty',
            'Referer': 'https://www.autotrader.ca/cars/on/london/?rcp=50&rcs={}&srt=9&prx=1000&prv=Ontario&loc=n6b3r1&hprc=True&wcp=True&adtype=Private&inMarket=advancedSearch',
            # 'Accept-Encoding': 'gzip, deflate, br',
            'Priority': 'u=1, i',
            # 'Cookie': 'atOptUser=07c737ae-676c-40f6-96c6-fea0904dc57d; as24Visitor=130721fe-45dd-4393-91d3-1d5cca3e11ef; searchBreadcrumbs=%7B%22srpBreadcrumb%22%3A%5B%7B%22Text%22%3A%22Cars%2C%20Trucks%20%26%20SUVs%22%2C%22Url%22%3A%22%2Fcars%2F%3Frcp%3D25%26rcs%3D0%26srt%3D9%26prx%3D-1%26hprc%3DTrue%26wcp%3DTrue%26adtype%3DPrivate%22%7D%2C%7B%22Text%22%3A%22Ontario%22%2C%22Url%22%3A%22%2Fcars%2Fon%2F%3Frcp%3D25%26rcs%3D0%26srt%3D9%26prx%3D-2%26prv%3DOntario%26loc%3Dn6b3r1%26hprc%3DTrue%26wcp%3DTrue%26adtype%3DPrivate%22%7D%2C%7B%22Text%22%3A%22London%22%2C%22Url%22%3A%22%2Fcars%2Fon%2Flondon%2F%3Frcp%3D50%26rcs%3D0%26srt%3D9%26prx%3D1000%26prv%3DOntario%26loc%3Dn6b3r1%26hprc%3DTrue%26wcp%3DTrue%26adtype%3DPrivate%22%7D%5D%2C%22isFromSRP%22%3Afalse%2C%22neighbouringIds%22%3Anull%7D; visid_incap_820541=fmQpcehBR4mc6IUbvRUGPMhTA2kAAAAAQUIPAAAAAAA2yEGxXGFkjXQmhak2yB2H; nlbi_820541_1646237=MEDNGOwUTQuiKeecpRL4bAAAAACM8JeUVOw3B8bAoAPaCfjQ; incap_ses_475_820541=D1ngB77s0nIpba4ocIqXBslTA2kAAAAAEe6Z3X521K8cBj3lvIrmrw==; optimizelyEndUserId=oeu1761825745421r0.4037649605335607; cbnr=1; optimizelySession=1761825751335; _gcl_au=1.1.2029418894.1761825757; at_as24_site_exp=at; nlbi_820541_3122371=vt8ifvlMf395FI5JpRL4bAAAAAB1OULur5TUXYw+htmy17mF; __GTMADBLOCKER__=no; pCode=N6B3R1; srchLocation=%7B%22Location%22%3A%7B%22Address%22%3Anull%2C%22City%22%3A%22London%22%2C%22Latitude%22%3A42.97735595703125%2C%22Longitude%22%3A-81.24272918701172%2C%22Province%22%3A%22ON%22%2C%22PostalCode%22%3A%22N6B%203R1%22%2C%22Type%22%3A%22%22%7D%2C%22UnparsedAddress%22%3A%22n6b3r1%22%7D; {E7ABF06F-D6A6-4c25-9558-3932D3B8A04D}=; lastsrpurl=/cars/on/london/?rcp=50&rcs={}&srt=9&prx=1000&prv=Ontario&loc=n6b3r1&hprc=True&wcp=True&adtype=Private&inMarket=advancedSearch; PageSize=50; SortOrder=CreatedDateDesc; _switch_session_id=c04b8b72-a7d9-4d92-8562-8011a349f0df; _rdt_uuid=1761825766275.249ef6bd-1e8a-49b2-bfa6-4d4b449fcb5f; ci_uid=1c04ac02-3707-4e74-8f2d-9ee6ca34b0b0; _cc_id=5fc3c25bd8643375c9ac9dda701a58db; panoramaId=e64469f18895889a88b48791f937185ca02c2d16ce1c7df0f548498579f7dd96; _ga=GA1.1.161662328.1761825771; _ga_PHSPDB57ZK=GS2.1.s1761825771$o1$g1$t1761825771$j60$l0$h520580996; _uetsid=5cfa8170b58811f099452b3056482c66; _uetvid=5cfb0100b58811f082f2eb6a115d961c; FPID=FPID2.2.2DDrR4YiRyrMKqC17qzshJIbe7wk162DtP8QXAjF0Gk%3D.1761825771; FPAU=1.1.2029418894.1761825757; FPLC=In0ZYC6OrYrUVKn%2BxWA0VTcCFoSeGW4pBVM1JKKph0%2Fx6ZDg84Awr8wdGZGwmzN8lrdS1AI7kbnw8n%2FSNHuWrhN7JH3fw42ioGMRwLsHgidau0sfeXB1rN6NX32mFA%3D%3D; _fbp=fb.1.1761825774555.1206315652; _switch_session=eyJjbGlja2lkcyI6e30sImNvb2tpZXMiOnsicmR0X3V1aWQiOiIxNzYxODI1NzY2Mjc1LjI0OWVmNmJkLTFlOGEtNDliMi1iZmE2LTRkNGI0NDlmY2I1ZiIsImdhIjoiR0ExLjEuMTYxNjYyMzI4LjE3NjE4MjU3NzEiLCJmYnAiOiJmYi4xLjE3NjE4MjU3NzQ1NTUuMTIwNjMxNTY1MiJ9LCJpcEFkZHJlc3MiOiIxOTYuMTMxLjI1NS4zNyIsInVzZXJBZ2VudCI6Ik1vemlsbGEvNS4wIChXaW5kb3dzIE5UIDEwLjA7IFdpbjY0OyB4NjQpIEFwcGxlV2ViS2l0LzUzNy4zNiAoS0hUTUwsIGxpa2UgR2Vja28pIENocm9tZS8xMzkuMC4wLjAgU2FmYXJpLzUzNy4zNiIsImVtIjpbXSwicGgiOltdLCJzaWQiOiJjMDRiOGI3Mi1hN2Q5LTRkOTItODU2Mi04MDExYTM0OWYwZGYiLCJzdGFydF90aW1lIjoxNzYxODI1NzYyODE4LCJhY2NvdW50X2lkIjoiazhuYW9tdUZyZzA4aWdaMyIsInVybCI6Imh0dHBzOi8vd3d3LmF1dG90cmFkZXIuY2EvY2Fycy9vbi9sb25kb24vP3JjcD01MCZyY3M9e30mc3J0PTkmcHJ4PTEwMDAmcHJ2PU9udGFyaW8mbG9jPW42YjNyMSZocHJjPVRydWUmd2NwPVRydWUmYWR0eXBlPVByaXZhdGUmaW5NYXJrZXQ9YWR2YW5jZWRTZWFyY2gifQ==; _ga_RMZMLXC8S1=GS2.1.s1761825775$o1$g0$t1761825775$j60$l0$h0; sa-user-id=s%253A0-a5f9c688-6af2-597c-7a50-6ac21ea78c15.oPMX3gBxrQ3KEhs4lVkEXTKan24hYMufc8rb2OK7TWo; sa-user-id-v2=s%253ApfnGiGryWXx6UGrCHqeMFcSD_yU.p4CjvqHIcwdpU3B5FXXIWxDfPSMf1elKblDyjBSEgII; sa-user-id-v3=s%253AAQAKIP0Xy0c_9ZFajRI89pA9Zps06LE952BO6gBlBWZKWjApEAEYAyDwp43IBjABOgTIcrGlQgTck8g-.XxJ1WOOjRyqsMvlfFwc2DXZ9%252Fn1tfUuFKd8zeV15gOA; tgcid=161662328.1761825771; panoramaId_expiry=1762430577631; panoramaIdType=panoDevice; cc_audpid=5fc3c25bd8643375c9ac9dda701a58db; _scor_uid=b81be454d6d144979ea4cd0af7fe7185; _clck=b6qezn%5E2%5Eg0l%5E0%5E2129; _tt_enable_cookie=1; _ttp=01K8TFZWA74293RG043WN8QZVH_.tt.1; __qca=P1-51907248-63d9-487d-a7da-d35082f53b6d; _td=568ab9ea-4918-4923-a88a-88a99a4feca6; _pin_unauth=dWlkPVlUZzVOMk5sWm1RdE1XUTJOQzAwWkRjeUxXRmtaVEF0WVRSak16Um1NV1F3Tnpoaw; FCCDCF=%5Bnull%2Cnull%2Cnull%2Cnull%2Cnull%2Cnull%2C%5B%5B32%2C%22%5B%5C%225e9f1905-80e2-414a-b119-56a12b5e5111%5C%22%2C%5B1761825779%2C74000000%5D%5D%22%5D%5D%5D; __T2CID__=b6272444-9f25-4552-8030-201ff15e8bc1; FCNEC=%5B%5B%22AKsRol_na-AQ6_R8pdXUdUL18Dftq3r-DQnYI0i-q-tixcAMRWsCiq7TLYFedKGp5ZDhL41Bo5_-X6rqXHazLA52R81Vx7A0x-cyefbHWzmHyjTx-GEmyIMO4IbBlexLzz0mnFaqenFgV43IyhVMxeepa36cItNNHg%3D%3D%22%5D%5D; cto_bundle=ixD78l9HMzV6MlJnYSUyQkpCUGVBM3REJTJCc0REOWFiQVBRT2daeGQlMkZpZ0VERjElMkJXSWRDJTJGbUtPMyUyQllDRU5OVXlSYTZTYkFKaVJvdURzekxRNTRHSEV0R1clMkJhSSUyQmJFbTlWUzlPOUc3YkFUV29tN1plOXZsWU95enJ1V0UzRm1VZWVjMUZQSUtiWmNiNVo3SmsySWJRdGpkWlpFV3dMblRNSHkwYkltVVBldUlYRiUyQjlIcGMlM0Q; _clsk=1q07egb%5E1761826572802%5E2%5E1%5El.clarity.ms%2Fcollect; _ga_PCMZZ2EWK8=GS2.1.s1761825776$o1$g1$t1761826574$j60$l0$h0; ttcsid=1761825780107::Cotp8QHVqvwLanwIJaWl.1.1761826591926.0; ttcsid_C7TFG3E0MJON0LQMRBS0=1761825780093::e7nW3pAuDE1nClseStGA.1.1761826591926.0; searchState={"isUniqueSearch":false,"make":null,"model":null}',
        }

        json_data = {
            'micrositeType': 1,
            'Microsite': {
                'SiteId': 2,
                'MicrositeType': 1,
                'Culture': 'en-CA',
                'LandingUrlSegment': 'cars',
                'Keyword': None,
                'SearchResultsUrlSegment': 'cars',
                'ResearchUrlSegment': None,
                'ResearchDisplayText': None,
                'DisplayText': 'Cars, Trucks & SUVs',
                'ShortName': 'Car',
                'MediumName': None,
                'ShortNameGender': '',
                'RequiresType': False,
                'RequiresSubType': False,
                'Category2Ids': [
                    7,
                    9,
                    10,
                    11,
                ],
                'DisableSeoModel': False,
                'DefaultWithPrice': True,
                'DefaultWithPhotos': True,
                'IsNpv': False,
                'DisplayNeuvesInNpvPopularLinks': False,
                'NextPrevSearchCriteriaOverrides': None,
                'TrackingName': 'Car',
            },
            'Address': 'n5x0e2',
            'Proximity': 1000,
            'WithFreeCarProof': False,
            'WithPrice': True,
            'WithPhotos': True,
            'HasLiveChat': False,
            'HasVirtualAppraisal': False,
            'HasHomeTestDrive': False,
            'HasOnlineReservation': False,
            'HasDigitalRetail': False,
            'HasDealerDelivery': False,
            'HasHomeDelivery': False,
            'HasTryBeforeYouBuy': False,
            'HasMoneyBackGuarantee': False,
            'IsNew': True,
            'IsUsed': True,
            'IsDamaged': True,
            'IsCpo': True,
            'IsDealer': False,
            'IsPrivate': True,
            'IsOnlineSellerPlus': False,
            'Top': 50,
            'Make': None,
            'Model': None,
            'BodyType': None,
            'PriceAnalysis': None,
            'PhoneNumber': '',
            'PriceMin': None,
            'PriceMax': None,
            'WheelBaseMin': None,
            'WheelBaseMax': None,
            'EngineSizeMin': None,
            'EngineSizeMax': None,
            'LengthMin': None,
            'LengthMax': None,
            'WeightMin': None,
            'WeightMax': None,
            'HorsepowerMin': None,
            'HorsepowerMax': None,
            'HoursMin': None,
            'HoursMax': None,
            'OdometerMin': None,
            'OdometerMax': None,
            'YearMin': None,
            'YearMax': None,
            'Keywords': '',
            'FuelTypes': None,
            'Transmissions': None,
            'Colours': None,
            'Drivetrain': None,
            'Engine': None,
            'SeatingCapacity': None,
            'NumberOfDoors': None,
            'Sleeps': None,
            'SlideOuts': None,
            'Trim': None,
            'RelatedCompanyOwnerCompositeId': None,
            '': None,
            'SrpNewCarWidgetVariant': None,
            'IsUniqueSearch': False,
            'InMarketType': 'advancedSearch',
            'Skip': 0,
            'SortBy': 'CreatedDateDesc',
        }

        response = requests.post(
            'https://www.autotrader.ca/Refinement/Search',
            cookies=cookies,
            headers=headers,
            json=json_data,
            verify=False,
        )
        print("+++++++++++++++++++++++++++++++++++++++++")
        print(response.text)
        print("+++++++++++++++++++++++++++++++++++++++++")
        data = json.loads(response.text)
        mydata = data['AdsHtml']
        html = mydata

        soup = BeautifulSoup(html, "html.parser")
        cars = []

        for wrapper in soup.find_all("div", class_="dealer-split-wrapper"):
            car = {}

            # --- Title ---
            title_tag = wrapper.find("span", class_="title-with-trim")
            car["title"] = title_tag.get_text(strip=True) if title_tag else None

            # --- Price ---
            price_tag = wrapper.find("span", class_="price-amount")
            car["price"] = price_tag.get_text(strip=True) if price_tag else None

            # --- Location ---
            location_tag = wrapper.find("span", class_="proximity-text overflow-ellipsis")
            car["location"] = location_tag.get_text(strip=True) if location_tag else None

            # --- Odometer ---
            odometer_tag = wrapper.find("span", class_="odometer-proximity")
            car["odometer"] = odometer_tag.get_text(strip=True) if odometer_tag else None

            # --- Image ---
            image_tag = (
                wrapper.find("img", class_="photo-image") or  # match loosely
                wrapper.find("img")  # fallback: any <img> inside listing
            )

            image_url = None
            if image_tag:
                # check common attributes for image URL
                for attr in ["data-original", "data-src", "src"]:
                    if image_tag.get(attr) and not image_tag[attr].startswith("data:image"):
                        image_url = image_tag[attr]
                        break

            car["image_src"] = image_url

            base_url = "https://www.autotrader.ca"
            ad_tag = wrapper.find("a", class_="inner-link")
            car["adLink"] = ad_link = base_url + ad_tag["href"] if ad_tag and ad_tag.has_attr("href") else None
            
            insert_car_autotreader(car["title"], car["price"], car["location"], car["odometer"], car["image_src"], car["adLink"])
            # cars.append(car)
        st.success("✅ Done! Autotrader Cars successfully added to the database.")

        # print(json.dumps(cars, indent=4, ensure_ascii=False))

