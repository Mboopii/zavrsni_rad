#koristi službeni Python runtime kao parent image
FROM python:3.12-slim

#postavi radni direktorij u kontejneru
WORKDIR /app

#kopiraj requirements.txt datoteku prvo kako bi iskoristio Docker cache
COPY requirements.txt /app/requirements.txt

#instaliraj potrebne pakete specificirane u requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

#kopiraj trenutni direktorij sadržaja u kontejner na /app
COPY . /app

#omogući port 5000 za svijet izvan ovog kontejnera
EXPOSE 5000

#definiraj varijablu okruženja
ENV NAME World

#pokreni app.py kada se kontejner pokrene
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "--threads", "2", "app:app"]
