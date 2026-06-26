FROM node:20-alpine
WORKDIR /app
COPY package.json ./
RUN npm config set registry https://registry.npmjs.org/ && npm install --no-audit --no-fund
COPY . .
EXPOSE 5173
CMD ["npm", "run", "dev"]
