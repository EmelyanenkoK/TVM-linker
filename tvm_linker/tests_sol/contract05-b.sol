pragma solidity ^0.5.0;

contract IRemoteContract {
	function remoteMethod(uint16 x) public;
}

contract IRemoteContractCallback {
	function remoteMethodCallback(uint16 x) public;
}

contract RemoteContract is IRemoteContract {

	uint16 m_value;
	
	// A method to be called from another contract
	
	function remoteMethod(uint16 x) public {
		m_value = x;
		IRemoteContractCallback(msg.sender).remoteMethodCallback(x * 16);
		return; 
	}
	
}
