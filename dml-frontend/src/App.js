import React, { Component } from 'react';
import axios from 'axios';
import FileBase64 from 'react-file-base64'
import './App.css';

class App extends Component {
  constructor(props) {
    super(props);
    this.state = {
      files: [],
      prediction: ''
    }
  }
    
  getFiles(files){
    this.setState({ files: files })
  }

  submitImage = () => {
    axios.post('http://localhost:5000/predict-fruit', {
      image: this.state.files[0].base64.split(',')[1]
    })
    .then(response => {
      this.setState({
        prediction: response.data.fruit
      })
    })
    .catch(function (error) {
      console.log(error);
    });
  }

  render() {
    return (
      <div className="App">
        <div className="App-header">
          <img src={'https://png2.cleanpng.com/sh/68bfd286dd7ba14383e06b77feffc659/L0KzQYm3VMI3N5R8fZH0aYP2gLBuTf1ia5luhtc2bHXkgrBwjvcubJZqiJ91ZXH1frr1h71ieqVufttsaXHvPbr1lPVtdJpsRdRyb33odLrqgfwuPZJqSdZsMUXkR4fpUcYvOGM5S6k7OUO0RYO7V8UyO2k2TqoAOD7zfri=/kisspng-machine-learning-deep-learning-artificial-intellig-biomedical-5ae1dc15a76b16.0243729315247513816858.png'} className="App-logo" alt="logo" />
          <h2>Distributed Machine Learning App</h2>
        </div>
        <div className="container main-container">
          <div className="row">
            <div class="col-sm top-margin">
              <FileBase64
                multiple={ true }
                onDone={ this.getFiles.bind(this) } />
              <div className="text-center">
                { this.state.files.map((file,i) => {
                  return <img key={i} src={file.base64} className="img-container"/>
                }) }
                <img src="" />
              </div>
              {
                this.state.files.length > 0 ? <div className="btn-container">
                  <button onClick={this.submitImage} className="learn-more">Submit Image</button>
                </div> : null
              }                
            </div>
            <div class="col-sm prediction-text">
              {this.state.prediction}
            </div>
          </div>
        </div>

      </div>
    );
  }
}

export default App;
