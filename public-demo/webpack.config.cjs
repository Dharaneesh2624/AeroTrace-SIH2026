const path=require('node:path');
const HtmlWebpackPlugin=require('html-webpack-plugin');
const CopyPlugin=require('copy-webpack-plugin');
module.exports={entry:'./src/main.tsx',output:{path:path.resolve(__dirname,'dist'),filename:'app.[contenthash].js',publicPath:'./'},
  resolve:{extensions:['.tsx','.ts','.js']},
  module:{rules:[{test:/\.tsx?$/,exclude:/node_modules/,use:{loader:'ts-loader',options:{transpileOnly:true,compilerOptions:{noEmit:false,allowImportingTsExtensions:false}}}},
    {test:/\.css$/,use:['style-loader','css-loader']}]},
  plugins:[new HtmlWebpackPlugin({template:'index.html'}),new CopyPlugin({patterns:[{from:'public',to:'.'}]})],
  optimization:{splitChunks:{chunks:'all'}},performance:{hints:false},devtool:false};
