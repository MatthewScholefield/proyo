import moment from 'moment';
import React from 'react';
import ReactDOM from 'react-dom';

import './index.css';
import App from './App';

moment.locale();

ReactDOM.render(<App />, document.getElementById('root'));
