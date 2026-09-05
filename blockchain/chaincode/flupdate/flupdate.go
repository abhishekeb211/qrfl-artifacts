package main

import (
	"encoding/json"
	"fmt"

	"github.com/cloudflare/circl/sign/mldsa/mldsa65"
	"github.com/hyperledger/fabric-contract-api-go/contractapi"
)

// FLUpdateContract verifies PQC-signed federated learning update payloads.
// Fabric MSP remains ECDSA P-256; PQC verification occurs at application layer.
type FLUpdateContract struct {
	contractapi.Contract
}

type FLUpdate struct {
	ClientID  string `json:"clientId"`
	Round     int    `json:"round"`
	Payload   []byte `json:"payload"`
	PublicKey []byte `json:"publicKey"`
	Signature []byte `json:"signature"`
}

type StoredUpdate struct {
	FLUpdate
	Verified bool   `json:"verified"`
	TxMode   string `json:"txMode"`
}

func (c *FLUpdateContract) SubmitUpdate(ctx contractapi.TransactionContextInterface, updateJSON string) error {
	var update FLUpdate
	if err := json.Unmarshal([]byte(updateJSON), &update); err != nil {
		return fmt.Errorf("invalid update JSON: %w", err)
	}
	verified, err := verifyMLDSA65(update.PublicKey, update.Payload, update.Signature)
	if err != nil {
		return fmt.Errorf("signature verification failed: %w", err)
	}
	stored := StoredUpdate{FLUpdate: update, Verified: verified, TxMode: "native_pq"}
	bytes, err := json.Marshal(stored)
	if err != nil {
		return err
	}
	key := fmt.Sprintf("%s:%d", update.ClientID, update.Round)
	return ctx.GetStub().PutState(key, bytes)
}

func (c *FLUpdateContract) GetUpdate(ctx contractapi.TransactionContextInterface, clientID string, round int) (*StoredUpdate, error) {
	key := fmt.Sprintf("%s:%d", clientID, round)
	bytes, err := ctx.GetStub().GetState(key)
	if err != nil {
		return nil, err
	}
	if bytes == nil {
		return nil, fmt.Errorf("update not found")
	}
	var stored StoredUpdate
	if err := json.Unmarshal(bytes, &stored); err != nil {
		return nil, err
	}
	return &stored, nil
}

func verifyMLDSA65(publicKey, message, signature []byte) (bool, error) {
	pk := new(mldsa65.PublicKey)
	if err := pk.UnmarshalBinary(publicKey); err != nil {
		return false, err
	}
	valid := mldsa65.Verify(pk, message, nil, signature)
	return valid, nil
}

func main() {
	chaincode, err := contractapi.NewChaincode(new(FLUpdateContract))
	if err != nil {
		panic(err)
	}
	if err := chaincode.Start(); err != nil {
		panic(err)
	}
}
