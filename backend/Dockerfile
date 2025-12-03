FROM node:20.19.4-alpine

WORKDIR /app

COPY package*.json ./

RUN npm install

COPY . .

RUN mkdir -p uploads

EXPOSE 4000

CMD ["npm", "start"]
