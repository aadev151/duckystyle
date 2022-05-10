from flask_restful import Resource, abort
from flask import jsonify

from . import db_session
from .dfts import Dft


class DftResource(Resource):
    def get(self, dft_id):
        session = db_session.create_session()
        dft = session.query(Dft).get(dft_id)
        if not dft:
            abort(message='DFT not found')

        return jsonify({
            'dft': dft.to_dict(only=('id', 'name', 'price', 'owner')),
            'url': 'https://duckystyle.pythonanywhere.com/dft/' + str(dft.id)
        })


class DftListResource(Resource):
    def get(self):
        session = db_session.create_session()
        dfts = session.query(Dft).all()
        return jsonify(
            {
                'dfts':
                    [
                        {
                            'dft': item.to_dict(only=('id', 'name', 'price', 'owner')),
                            'url': 'https://duckystyle.pythonanywhere.com/dft/' + str(item.id)
                        } for item in dfts
                    ]
            }
        )
