# first our build environment
FROM node:16 as build

# pass on the commandline like --build-arg env=local (stage | production)
ARG env=local
# use after this line like `$env`

WORKDIR /build
COPY . .
RUN yarn
RUN yarn build


# production environment
FROM python:3.8

WORKDIR /j4ne

# load our repo into the container .. TODO skip /src ?
COPY . .

# load our front end from the build environment
COPY --from=build /build/build ./build

#build our python environment
RUN pip install -r requirements.txt

#open the web interface
EXPOSE 8001

#launch the back end
CMD python j4ne.py
# CMD /bin/bash