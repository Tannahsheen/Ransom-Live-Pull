Pulls everyone that has been posted on ransomware.live in the United States in the last N days. (this could easily be modified to other locations and timeframes) It outputs a list to verify none of your clients or partners show up on it.

This is pretty ugly, but it works for what I needed. Might help for somebody else too. 

git clone https://github.com/Tannahsheen/Ransom-Live-Pull.git

cd Ransom-Live-Pull

pip install requests python-dateutil beautifulsoup4

python3 pull.py 

you should have a .csv of the last 14 days of information shown on ransomware.live. 
